"""Agent core: sends buyer intent + tool definitions to the LLM, executes
whichever tool the model chooses, feeds the result back, and repeats until
the agent produces a final answer.

Every tool call is routed through guardrails.py (spend cap + whitelist) and
logged via audit.py before the result is returned to the model, so the model
cannot bypass the safety layer regardless of what it decides to do.
"""
import json
import os

from groq import Groq

from . import audit, catalog, guardrails, payments

MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

SYSTEM_PROMPT = """You are CartPilot, a checkout agent acting on behalf of a buyer on a \
Razorpay merchant's store. You can search the catalog, apply discount codes, and create a \
payment. Always search before recommending a product. Prefer the cheapest product that \
matches the buyer's request unless they ask otherwise. If a discount code is available, \
apply it before creating the payment. Only call create_payment once you have a final \
product and price. Never invent products, prices, or discount codes that were not returned \
by a tool call. If a tool call fails or is blocked, explain why to the buyer instead of \
retrying blindly."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_catalog",
            "description": "Search the merchant catalog for products matching a query, optionally filtered by max price (INR).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Free-text search, e.g. 'wireless earbuds'"},
                    "max_price": {"type": "number", "description": "Optional max price in INR"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_discount",
            "description": "Apply a discount code to a specific product and get the discounted price.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string"},
                    "code": {"type": "string", "description": "Discount code, e.g. WELCOME10"},
                },
                "required": ["product_id", "code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_payment",
            "description": "Create a Razorpay test-mode payment order for a final amount and product.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount_inr": {"type": "number"},
                    "product_id": {"type": "string"},
                },
                "required": ["amount_inr", "product_id"],
            },
        },
    },
]


def _execute_tool(name: str, args: dict, session_id: str) -> dict:
    """Run one tool call through guardrails, execute it, and log the outcome."""
    try:
        guardrails.check_action_allowed(name)

        if name == "search_catalog":
            result = {"results": catalog.search_catalog(**args)}
        elif name == "apply_discount":
            result = catalog.apply_discount(**args)
        elif name == "create_payment":
            guardrails.check_spend_cap(args["amount_inr"])
            result = payments.create_payment(**args)
        else:  # pragma: no cover - guarded by check_action_allowed above
            raise guardrails.GuardrailViolation(f"Unhandled action: {name}")

        audit.log_event("tool_call", {"tool": name, "args": args, "result": result}, session_id)
        return result

    except guardrails.GuardrailViolation as e:
        blocked = {"error": "guardrail_blocked", "reason": str(e)}
        audit.log_event("guardrail_block", {"tool": name, "args": args, "reason": str(e)}, session_id)
        return blocked

    except ValueError as e:
        failed = {"error": "tool_error", "reason": str(e)}
        audit.log_event("tool_error", {"tool": name, "args": args, "reason": str(e)}, session_id)
        return failed


def run_agent(buyer_intent: str, session_id: str | None = None, max_steps: int = 6) -> dict:
    """Run the agent loop for one buyer intent. Returns the final answer plus
    the list of tool calls made (for display in the demo UI).
    """
    session_id = session_id or audit.new_session_id()
    audit.log_event("session_start", {"buyer_intent": buyer_intent}, session_id)

    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": buyer_intent},
    ]

    trace = []

    for _ in range(max_steps):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        msg = response.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            audit.log_event("final_answer", {"content": msg.content}, session_id)
            return {"session_id": session_id, "answer": msg.content, "trace": trace}

        for tool_call in msg.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")
            result = _execute_tool(name, args, session_id)
            trace.append({"tool": name, "args": args, "result": result})
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                }
            )

    audit.log_event("max_steps_reached", {}, session_id)
    return {
        "session_id": session_id,
        "answer": "Reached the step limit before finishing — see trace for what happened.",
        "trace": trace,
    }
