# CartPilot — an AI checkout agent for Razorpay merchants

**Track:** AI Growth & Agentic Commerce
**Built for:** Razorpay AI Buildathon 2026

## Problem

Today, buying something from a merchant on Razorpay requires a human to browse, decide,
and manually complete checkout. As AI shopping agents (via emerging protocols like NPCI's
UAP, ACP, AP2, x402) become common, merchants need a way to be **"transactable by an AI
buyer"** — an AI agent should be able to complete a purchase on a merchant's behalf without
a human clicking through a UI. Most merchant checkout flows today are built for humans, not
agents, so there is no safe, bounded, explainable way for an AI to say "buy this" and have
it actually happen.

## Objectives

1. **Agent-readable commerce** — expose a merchant's catalog and checkout flow in a way an
   AI agent can query, reason over, and act on (not just a human-facing UI).
2. **Autonomous purchase completion** — go from a natural-language buyer intent
   (`"get me wireless earbuds under ₹2000"`) all the way to a completed payment, with no
   manual steps in between.
3. **Bounded, safe money actions** — every payment action is constrained by explicit
   guardrails (hard spend cap, allowed-action whitelist) so an autonomous agent can never
   overspend or take an unintended action.
4. **Explainability & auditability** — every decision the agent makes (why it picked a
   product, why a discount applied, why payment was triggered or blocked) is logged to a
   structured, human-reviewable audit trail.
5. **Merchant revenue growth** — the agent can apply upsell/cross-sell and discount rules to
   increase order value, not just complete the minimum transaction.

## Architecture

```
Buyer intent (text)
       │
       ▼
┌─────────────────┐      ┌───────────────────┐
│   Agent Core     │◄────►│  LLM (Groq API)    │  reasons over intent,
│  (agent.py)      │      │  tool-calling loop  │  decides which tool to call
└────────┬─────────┘      └────────────────────┘
         │ calls tools
         ▼
┌─────────────────────────────────────────────┐
│  Tools                                        │
│  • search_catalog()      (catalog.py)         │
│  • apply_discount()      (catalog.py)         │
│  • create_payment()      (payments.py)        │
└────────┬──────────────────────────────────────┘
         │ every tool call passes through
         ▼
┌─────────────────────────────────────────────┐
│  Guardrails (guardrails.py)                   │
│  • hard spend cap                             │
│  • allowed-action whitelist                   │
│  • blocks + logs anything outside bounds      │
└────────┬──────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│  Audit Log (audit.py)                         │
│  every decision + tool call + outcome,        │
│  written to audit_log.jsonl                   │
└─────────────────────────────────────────────┘
```

- **`agent.py`** — the reasoning loop. Sends the buyer's intent + tool definitions to the
  Groq LLM, executes whichever tool the model chooses, feeds the result back, repeats until
  the agent produces a final answer or completes a payment.
- **`catalog.py`** — a mock merchant catalog (`catalog.json`) plus search and discount-rule
  logic. Stands in for a real merchant's product API.
- **`payments.py`** — wraps Razorpay's **test-mode** Orders API. If no Razorpay test keys are
  configured, it automatically falls back to a **mock payment mode** that simulates the same
  response shape, so the whole agent is runnable and demoable with zero external
  credentials.
- **`guardrails.py`** — the safety layer every tool call passes through: a hard rupee spend
  cap per session, and a whitelist of actions the agent is allowed to take. Anything outside
  bounds is blocked and logged, not silently ignored.
- **`audit.py`** — append-only structured log (`audit_log.jsonl`) of every reasoning step,
  tool call, and outcome — the explainability layer.
- **`app.py`** — a Streamlit demo UI: type a buyer request, watch the agent think, search,
  apply discounts, and check out, with the live audit trail rendered alongside.

## Guardrails (safety-by-design)

| Guardrail | Enforced in | Behavior |
|---|---|---|
| Spend cap | `guardrails.py` | Payment blocked if order total exceeds `MAX_SPEND_INR` |
| Action whitelist | `guardrails.py` | Only `search_catalog`, `apply_discount`, `create_payment` are callable — anything else is rejected |
| Audit trail | `audit.py` | Every tool call, decision, and guardrail block is logged with a timestamp and reason |
| Mock/live payment separation | `payments.py` | Defaults to mock mode; live Razorpay test-mode calls only fire when `RAZORPAY_KEY_ID`/`RAZORPAY_KEY_SECRET` are set, and only ever against Razorpay's test environment |

## Setup

```bash
git clone <this-repo>
cd cartpilot
pip install -r requirements.txt
cp .env.example .env
# edit .env: add GROQ_API_KEY (required)
# optionally add RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET (test-mode) for live payment calls
```

### Run the CLI demo (no external keys beyond Groq needed)

```bash
python demo_cli.py "get me wireless earbuds under 2000 rupees"
```

### Run the Streamlit demo

```bash
streamlit run app.py
```

### Run the guardrail / catalog sanity tests (no API key needed)

```bash
python -m pytest tests/ -v
```

## Example run

```
Buyer: "get me wireless earbuds under 2000 rupees, and apply any discount you can"

Agent:
  → search_catalog(query="wireless earbuds", max_price=2000)
  → found: "BassPods X2" — ₹1,799
  → apply_discount(product_id="BP-X2", code="WELCOME10")
  → discounted total: ₹1,619.10
  → create_payment(amount=1619.10, product_id="BP-X2")
  → guardrail check: 1619.10 <= MAX_SPEND_INR (5000) ✅
  → payment created: order_id=order_mock_8f2a1c, status=created

Audit trail written to audit_log.jsonl (5 entries)
```

## What's stubbed / next steps

- Catalog is a static JSON file — a real deployment would pull from a merchant's live
  product API.
- Payment defaults to mock mode; wiring in real Razorpay test-mode keys is a one-line env
  var change (see `payments.py`).
- Guardrails currently cover spend cap + action whitelist; a production version would add
  per-merchant rate limiting and anomaly detection (natural extension into the AI Risk
  Manager track).

## Failure recovery (what broke during development)

- Early version let the LLM call `create_payment` with an unbounded amount if it
  misread the discount math — fixed by moving the spend check into `guardrails.py` as a
  hard gate *before* the payment tool executes, not just a prompt instruction the model
  could ignore.
- Mock payment mode was added after realizing the demo needed to run without live Razorpay
  test credentials in front of a panel — `payments.py` now detects missing keys and falls
  back automatically instead of crashing.
