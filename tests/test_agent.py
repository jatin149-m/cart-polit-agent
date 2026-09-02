"""Sanity tests that don't require any API keys — cover catalog search,
discount math, guardrail enforcement, and mock payment creation.

Run with: python -m pytest tests/ -v
"""
import pytest

from cartpilot import catalog, guardrails, payments


def test_search_catalog_finds_earbuds_under_budget():
    results = catalog.search_catalog("wireless earbuds", max_price=2000)
    assert len(results) == 1
    assert results[0]["product_id"] == "BP-X2"


def test_search_catalog_respects_price_filter():
    results = catalog.search_catalog("wireless earbuds", max_price=1000)
    assert results == []


def test_apply_discount_math():
    breakdown = catalog.apply_discount("BP-X2", "WELCOME10")
    assert breakdown["original_price_inr"] == 1799.0
    assert breakdown["final_price_inr"] == pytest.approx(1619.1, abs=0.01)


def test_apply_discount_unknown_code_raises():
    with pytest.raises(ValueError):
        catalog.apply_discount("BP-X2", "NOTREAL")


def test_apply_discount_unknown_product_raises():
    with pytest.raises(ValueError):
        catalog.apply_discount("NOT-A-PRODUCT", "WELCOME10")


def test_guardrail_blocks_action_not_on_whitelist():
    with pytest.raises(guardrails.GuardrailViolation):
        guardrails.check_action_allowed("delete_merchant_account")


def test_guardrail_allows_whitelisted_action():
    guardrails.check_action_allowed("create_payment")  # should not raise


def test_guardrail_blocks_spend_over_cap():
    with pytest.raises(guardrails.GuardrailViolation):
        guardrails.check_spend_cap(guardrails.MAX_SPEND_INR + 1)


def test_guardrail_blocks_non_positive_amount():
    with pytest.raises(guardrails.GuardrailViolation):
        guardrails.check_spend_cap(0)


def test_guardrail_allows_spend_within_cap():
    guardrails.check_spend_cap(guardrails.MAX_SPEND_INR - 1)  # should not raise


def test_mock_payment_creation():
    assert payments.is_live_mode() is False  # no keys set in test env
    result = payments.create_payment(amount_inr=1619.10, product_id="BP-X2")
    assert result["mode"] == "mock"
    assert result["status"] == "created"
    assert result["order_id"].startswith("order_mock_")
