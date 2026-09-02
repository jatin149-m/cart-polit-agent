"""Payment execution — wraps Razorpay's TEST-mode Orders API.

If RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET are not set, this module runs in
mock mode: it returns a response shaped exactly like Razorpay's real API so
the rest of the agent (and the demo) works identically either way. This lets
the whole project run and be demoed with zero external payment credentials,
while remaining a one-env-var change away from hitting Razorpay's real
test-mode endpoint.

NOTE: this module only ever talks to Razorpay's TEST environment. It never
handles live/production keys.
"""
import os
import uuid

_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")

_LIVE_MODE = bool(_KEY_ID and _KEY_SECRET)

if _LIVE_MODE:
    import razorpay  # only imported when actually needed

    _client = razorpay.Client(auth=(_KEY_ID, _KEY_SECRET))


def is_live_mode() -> bool:
    return _LIVE_MODE


def create_payment(amount_inr: float, product_id: str, receipt: str | None = None) -> dict:
    """Create a Razorpay order for the given amount (in INR).

    Returns a dict with at least: order_id, status, amount_inr, mode.
    """
    receipt = receipt or f"cartpilot_{uuid.uuid4().hex[:8]}"

    if _LIVE_MODE:
        order = _client.order.create(
            {
                "amount": int(round(amount_inr * 100)),  # paise
                "currency": "INR",
                "receipt": receipt,
                "notes": {"product_id": product_id, "source": "cartpilot-agent"},
            }
        )
        return {
            "order_id": order["id"],
            "status": order["status"],
            "amount_inr": amount_inr,
            "product_id": product_id,
            "mode": "live_test",
        }

    # --- mock mode ---
    return {
        "order_id": f"order_mock_{uuid.uuid4().hex[:8]}",
        "status": "created",
        "amount_inr": amount_inr,
        "product_id": product_id,
        "mode": "mock",
    }
