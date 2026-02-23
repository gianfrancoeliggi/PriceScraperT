"""Common scraper interface and orchestrator."""
import re
import logging
from typing import Any

import config


def clean_product_name(name: str) -> str:
    """
    Fix encoding mojibake and strip common junk from product names
    (e.g. "Quick shop", "Best Seller", "USD", size text, discount text).
    """
    if not name:
        return name
    # Fix common mojibake (UTF-8 interpreted as Latin-1)
    name = name.replace("\u00e2\u0084\u00a2", "\u2122")  # â¢ -> ™
    name = name.replace("\u00c2\u00ae", "\u00ae")        # Â® -> ®
    name = name.replace("\u00e2\u0084\u00a2", "\u2122")
    name = name.replace("â¢", "™").replace("Â®", "®")
    # Strip common junk phrases (case-insensitive where sensible)
    junk = [
        r"Quick\s*shop",
        r"Best\s*Seller",
        r"USD", r"GBP", r"EUR",
        r"Regular,\s*Petite,\s*Tall",
        r"\(\d+%\s*off\)",
        r"Save\s*\d+%",
        r"New!",
    ]
    for pattern in junk:
        name = re.sub(pattern, "", name, flags=re.IGNORECASE)
    # Collapse repeated brand/collection tags (e.g. "SPANXshape™SPANXshape™" -> "SPANXshape™")
    name = re.sub(r"(SPANX\w*™)\1+", r"\1", name, flags=re.IGNORECASE)
    # Remove repeated "SPANX...™...®" block (e.g. "SPANXshape™Booty Boost®SPANXshape™Booty Boost®" -> "SPANXshape™ Booty Boost®")
    name = re.sub(
        r"(SPANX\w*™)(.*?®)\1\2",
        r"\1 \2",
        name,
        flags=re.IGNORECASE,
    )
    # Trailing currency leftovers (e.g. "LeggingsUS" from "USD")
    name = re.sub(r"(US|GBP|EUR)\s*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:500] if name else name
from db import init_db
from db.write import save_scrape_results

logger = logging.getLogger(__name__)

# Each scraper module registers: brand_key -> callable that returns list[dict]
_REGISTRY: dict[str, Any] = {}


def register(brand_key: str):
    """Decorator to register a scraper function for a brand key."""

    def decorator(fn):
        _REGISTRY[brand_key] = fn
        return fn

    return decorator


def scrape_brand(brand_key: str) -> list[dict]:
    """
    Run the scraper for one brand. Returns list of items with keys:
    name, brand, category (optional), price, currency (optional), url.
    """
    if brand_key not in _REGISTRY:
        raise ValueError(f"Unknown brand key: {brand_key}. Known: {list(_REGISTRY.keys())}")
    fn = _REGISTRY[brand_key]
    return fn()


def run_all_scrapers(save: bool = True) -> tuple[list[dict], int, int]:
    """
    Run all registered scrapers, optionally persist to DB.
    Returns (all_items, total_products_updated, total_price_records_inserted).
    """
    all_items: list[dict] = []
    for key in config.BRAND_KEYS:
        if key not in _REGISTRY:
            logger.warning("No scraper registered for brand %s, skipping", key)
            continue
        try:
            items = scrape_brand(key)
            all_items.extend(items)
            logger.info("Scraper %s returned %d items", key, len(items))
        except Exception as e:
            logger.exception("Scraper %s failed: %s", key, e)
    products_updated = 0
    price_records_inserted = 0
    if save and all_items:
        init_db()
        products_updated, price_records_inserted = save_scrape_results(all_items)
    return all_items, products_updated, price_records_inserted
