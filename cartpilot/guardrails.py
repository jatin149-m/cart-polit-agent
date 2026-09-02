"""Safety layer every tool call passes through.

This is the enforcement point that keeps the agent's money-actions bounded.
Guardrail checks happen in code, not just as instructions to the LLM — a
misbehaving or manipulated model cannot bypass them.
"""
import os

MAX_SPEND_INR = float(os.environ.get("MAX_SPEND_INR", 5000))

ALLOWED_ACTIONS = {"search_catalog", "apply_discount", "create_payment"}


class GuardrailViolation(Exception):
    """Raised when a proposed agent action violates a guardrail."""


def check_action_allowed(action_name: str) -> None:
    if action_name not in ALLOWED_ACTIONS:
        raise GuardrailViolation(
            f"Action '{action_name}' is not in the allowed-action whitelist "
            f"{sorted(ALLOWED_ACTIONS)}."
        )


def check_spend_cap(amount_inr: float) -> None:
    if amount_inr > MAX_SPEND_INR:
        raise GuardrailViolation(
            f"Payment amount ₹{amount_inr:.2f} exceeds the session spend cap "
            f"of ₹{MAX_SPEND_INR:.2f}."
        )
    if amount_inr <= 0:
        raise GuardrailViolation(f"Payment amount ₹{amount_inr:.2f} must be positive.")
