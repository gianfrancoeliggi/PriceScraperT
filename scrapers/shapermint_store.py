"""Shapermint Store (shapermint.com) — one URL per category; price 1 unit and price for 2-pack when offered."""
import re
import time
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

import config
from scrapers.base import register, clean_product_name
from scrapers.browser import get_page_html

BRAND_NAME = "Shapermint Store"
BASE_URL = "https://shapermint.com"

# Category -> path (after /products/) for shapermint.com
SHAPERMINT_STORE_PRODUCTS = [
    ("EBRA", "truekind-supportive-comfort-wireless-shaping-bra-1?variant=40278561292422"),
    ("STBRA", "truekind-convertible-strapless-bandeau-bra-1?variant=40255864504454"),
    ("CAMI", "empetua-all-day-every-day-scoop-neck-cami-12?variant=40166475497606"),
    ("Sweetheart BRA", "shapermint-essentials-sweetheart-wireless-contour-bra-1?variant=41378475933830"),
    ("Tank CAMI", "shapermint-essentials-all-day-every-day-tank-cami-1?variant=41097985425542"),
    ("BRAHE", "truekind-everyday-comfort-wireless-shaping-bra-1?variant=40101754568838"),
    ("BSS", "all-day-every-day-high-waisted-shaper-shorts-5?variant=21578971676732"),
]


def _parse_price(s: str) -> Optional[float]:
    """Extract numeric price from string like '$29.99', '29.99'."""
    if not s:
        return None
    s = str(s).strip().replace(",", "")
    match = re.search(r"[\d]+\.?\d*", s)
    if match:
        return float(match.group())
    return None


def _scrape_product_page(category_label: str, product_path: str) -> list[dict]:
    """Load one shapermint.com product page; return items for 1-unit price and 2-pack price (if present)."""
    url = urljoin(BASE_URL, "/products/" + product_path.lstrip("/"))

    try:
        html = get_page_html(url, wait_selector="h1, [class*='price'], .price")
    except Exception as e:
        raise RuntimeError(f"Shapermint Store fetch failed {url}: {e}") from e

    soup = BeautifulSoup(html, "html.parser")
    title = ""
    h1 = soup.select_one("h1")
    if h1:
        title = (h1.get_text(strip=True) or "").strip()
        title = clean_product_name(title)
    if not title:
        title = f"Shapermint {category_label}"

    price_single: Optional[float] = None
    price_two: Optional[float] = None
    text = soup.get_text()

    # Main price: first $XX.XX that looks like a product price (often after strikethrough MSRP)
    for m in re.finditer(r"\$\s*([\d,]+\.?\d*)", text):
        p = _parse_price(m.group(1))
        if p is not None and 5 < p < 500:
            price_single = p
            break

    # "Get 2 for $XX.XX" or "Get 2 for 56% OFF" with price on next line / same block
    get2_match = re.search(r"Get\s+2\s+for\s+(?:\$?\s*([\d,]+\.?\d*)|(\d+)%\s*OFF)", text, re.IGNORECASE)
    if get2_match:
        if get2_match.group(1):
            price_two = _parse_price(get2_match.group(1))
        elif get2_match.group(2) and price_single:
            pct = int(get2_match.group(2)) / 100.0
            price_two = round(price_single * 2 * (1 - pct), 2)

    # Alternative: look for second price in common Shopify/theme patterns
    if price_two is None and price_single:
        # e.g. "$39.99 $80.00 Get 2 for 45% OFF"
        prices = re.findall(r"\$\s*([\d,]+\.?\d*)", text)
        for s in prices:
            p = _parse_price(s)
            if p is not None and p != price_single and 10 < p < 500:
                price_two = p
                break

    items = []
    if price_single is not None and price_single > 0:
        items.append({
            "name": title[:500],
            "brand": BRAND_NAME,
            "category": category_label,
            "price": price_single,
            "currency": "USD",
            "url": url,
            "base_url": BASE_URL,
        })
    if price_two is not None and price_two > 0:
        items.append({
            "name": f"{title} — 2 Pack"[:500],
            "brand": BRAND_NAME,
            "category": category_label,
            "price": price_two,
            "currency": "USD",
            "url": f"{url}&v=2pack" if "?" in url else f"{url}?v=2pack",
            "base_url": BASE_URL,
        })
    return items


@register("shapermint_store")
def scrape_shapermint_store() -> list[dict]:
    """Scrape shapermint.com product pages; return 1-unit and 2-pack prices per category."""
    all_items = []
    for category_label, product_path in SHAPERMINT_STORE_PRODUCTS:
        try:
            items = _scrape_product_page(category_label, product_path)
            all_items.extend(items)
        except Exception as e:
            raise RuntimeError(f"Shapermint Store ({category_label}) {product_path}: {e}") from e
        time.sleep(config.REQUEST_DELAY_SECONDS)
    return all_items
