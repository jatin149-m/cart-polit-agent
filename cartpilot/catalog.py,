"""Mock merchant catalog: search + discount rules.

Stands in for a real merchant's product API. In production this module would be
replaced with calls to the merchant's actual catalog/inventory service.
"""
import json
import os
from typing import Optional

_CATALOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "catalog.json")

# Discount codes a merchant might configure. Percentage off, in [0, 1].
DISCOUNT_CODES = {
    "WELCOME10": 0.10,
    "SAVE15": 0.15,
}


def _load_catalog() -> list[dict]:
    with open(_CATALOG_PATH, "r") as f:
        return json.load(f)


def search_catalog(query: str, max_price: Optional[float] = None) -> list[dict]:
    """Search the catalog by free-text query (matched against name/category),
    optionally filtered by max price. Returns matching products sorted by price.
    """
    query_lower = query.lower().strip()
    catalog = _load_catalog()

    results = []
    for item in catalog:
        haystack = f"{item['name']} {item['category']}".lower()
        # loose match: any query token appears in name/category
        tokens = [t for t in query_lower.split() if t]
        if not tokens or any(t in haystack for t in tokens):
            if max_price is None or item["price_inr"] <= max_price:
                results.append(item)

    results.sort(key=lambda i: i["price_inr"])
    return results


def get_product(product_id: str) -> Optional[dict]:
    for item in _load_catalog():
        if item["product_id"] == product_id:
            return item
    return None


def apply_discount(product_id: str, code: str) -> dict:
    """Apply a discount code to a product. Returns pricing breakdown.

    Raises ValueError if the product or code is invalid.
    """
    product = get_product(product_id)
    if product is None:
        raise ValueError(f"Unknown product_id: {product_id}")

    code_upper = code.strip().upper()
    pct_off = DISCOUNT_CODES.get(code_upper)
    if pct_off is None:
        raise ValueError(f"Unknown discount code: {code}")

    original = product["price_inr"]
    discounted = round(original * (1 - pct_off), 2)
    return {
        "product_id": product_id,
        "product_name": product["name"],
        "original_price_inr": original,
        "discount_code": code_upper,
        "discount_pct": pct_off,
        "final_price_inr": discounted,
    }
