"""Shapermint Store (shapermint.com) — HTML parsing (main price from known classes) with optional vision fallback."""
import os
import re
import time
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scrapers.base import register, clean_product_name
from scrapers.browser import get_page_html, get_page_screenshot
from scrapers.vision_price import extract_prices_from_image

import config

BRAND_NAME = "Shapermint Store"
BASE_URL = "https://shapermint.com"

# Valid price range to reject "Save $17" and other non-product amounts
_PRICE_MIN, _PRICE_MAX = 10.0, 200.0

SHAPERMINT_STORE_PRODUCTS = [
    ("EBRA", "truekind-supportive-comfort-wireless-shaping-bra-1?variant=40278561292422"),
    ("STBRA", "truekind-convertible-strapless-bandeau-bra-1?variant=40255864504454"),
    ("CAMI", "empetua-all-day-every-day-scoop-neck-cami-12?variant=40166475497606"),
    ("Sweetheart BRA", "shapermint-essentials-sweetheart-wireless-contour-bra-1?variant=41378475933830"),
    ("Tank CAMI", "shapermint-essentials-all-day-every-day-tank-cami-1?variant=41097985425542"),
    ("BRAHE", "truekind-everyday-comfort-wireless-shaping-bra-1?variant=40101754568838"),
    ("BSS", "all-day-every-day-high-waisted-shaper-shorts-5?variant=21578971676732"),
]


def _parse_price_value(s: str) -> Optional[float]:
    """Extract numeric price from '$37.99' or '37.99' or '34' (dollars part)."""
    if not s:
        return None
    s = str(s).strip().replace(",", "")
    m = re.search(r"[\d]+\.?\d*", s)
    if m:
        v = float(m.group())
        return v if _PRICE_MIN <= v <= _PRICE_MAX else None
    return None


# is_2pack: True = 2-pack price, False = single unit, None = unknown (assign by min/max later)
def _collect_all_prices_from_html(soup: BeautifulSoup) -> list[tuple[float, Optional[bool]]]:
    """
    Find ALL prices in Shapermint PDP using known classes. Returns list of (price, is_2pack).
    - p.css-mjomzf: full price; if element or child contains 'each' -> 2-pack, else single.
    - p.css-1ljv1mr: full price; unknown (None).
    - p.css-kh3dt4 + p.css-283epf: dollars + cents pairs; unknown (None).
    Then we sort and assign: if no 'each' hint, smallest = single, largest = 2-pack.
    """
    collected: list[tuple[float, Optional[bool]]] = []
    seen_prices: set[float] = set()

    def add(price: float, is_2pack: Optional[bool]):
        p = round(price, 2)
        if _PRICE_MIN <= p <= _PRICE_MAX and p not in seen_prices:
            seen_prices.add(p)
            collected.append((p, is_2pack))

    # 1) All p.css-mjomzf — check for "each" in element (e.g. $29.99<small>/each</small>)
    for el in soup.select("p.css-mjomzf"):
        text = (el.get_text(strip=True) or "").strip()
        full_html = str(el)
        p = _parse_price_value(text)
        if p is not None:
            # If "each" appears in this element (or in child like <small>/each</small>), it's 2-pack
            has_each = "each" in text.lower() or "each" in full_html.lower()
            add(p, True if has_each else False)

    # 2) All p.css-1ljv1mr — full price, no "each" hint
    for el in soup.select("p.css-1ljv1mr"):
        text = (el.get_text(strip=True) or "").strip()
        p = _parse_price_value(text)
        if p is not None:
            add(p, None)

    # 3) All pairs p.css-kh3dt4 (dollars) + p.css-283epf (cents) in document order
    dollars_els = soup.select("p.css-kh3dt4")
    cents_els = soup.select("p.css-283epf")
    for i in range(min(len(dollars_els), len(cents_els))):
        d_text = (dollars_els[i].get_text(strip=True) or "").strip()
        c_text = (cents_els[i].get_text(strip=True) or "").strip()[:2]
        d = re.search(r"\d+", d_text)
        if d and len(c_text) == 2 and c_text.isdigit():
            whole = int(d.group())
            p = whole + int(c_text) / 100.0
            if _PRICE_MIN <= p <= _PRICE_MAX:
                add(round(p, 2), None)

    return collected


def _single_and_2pack_from_collected(collected: list[tuple[float, Optional[bool]]]) -> tuple[Optional[float], Optional[float]]:
    """
    From list of (price, is_2pack), derive single unit price and 2-pack total price.
    - If we have (price, True) -> that's 2-pack per-unit ("each"), store as price × 2 (total pack).
    - If we have (price, False) -> that's single.
    - For (price, None): smallest = single, largest = 2-pack (already total on page).
    """
    price_single: Optional[float] = None
    price_2pack: Optional[float] = None
    unknown: list[float] = []

    for p, is_2pack in collected:
        if is_2pack is True:
            # "each" price: homogenize by storing total pack price (× 2)
            price_2pack = round(p * 2, 2)
        elif is_2pack is False:
            price_single = p
        else:
            unknown.append(p)

    if unknown:
        unknown.sort()
        if price_single is None and unknown:
            price_single = unknown[0]
        if price_2pack is None and len(unknown) >= 2:
            price_2pack = unknown[-1]
        elif price_2pack is None and len(unknown) == 1 and price_single is not None and unknown[0] != price_single:
            price_2pack = unknown[0]
        elif price_2pack is None and len(unknown) == 1 and price_single is None:
            price_single = unknown[0]

    return (price_single, price_2pack)


def _get_title_from_url(url: str) -> str:
    try:
        html = get_page_html(url, wait_selector="h1")
    except Exception:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.select_one("h1")
    if h1:
        t = (h1.get_text(strip=True) or "").strip()
        if t:
            return clean_product_name(t)
    return ""


def _scrape_product_page(category_label: str, product_path: str) -> list[dict]:
    """Try HTML parsing first (main price from known classes); fall back to vision if no API key or HTML fails."""
    url = urljoin(BASE_URL, "/products/" + product_path.lstrip("/"))
    try:
        html = get_page_html(url, wait_selector="h1, [class*='price'], .price, p.css-mjomzf, p.css-1ljv1mr, p.css-kh3dt4")
    except Exception as e:
        raise RuntimeError(f"Shapermint Store fetch failed {url}: {e}") from e
    soup = BeautifulSoup(html, "html.parser")
    title = ""
    h1 = soup.select_one("h1")
    if h1:
        t = (h1.get_text(strip=True) or "").strip()
        if t:
            title = clean_product_name(t)
    if not title:
        title = f"Shapermint {category_label}"

    collected = _collect_all_prices_from_html(soup)
    price_single, price_2pack = _single_and_2pack_from_collected(collected)

    # Fallback to vision only if HTML did not find main price and we have an API key
    if price_single is None and (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")):
        try:
            screenshot = get_page_screenshot(url, wait_selector="h1, [class*='price'], .price")
            prices = extract_prices_from_image(screenshot)
            price_single = prices.get("price_single")
            if price_2pack is None:
                price_2pack = prices.get("price_2pack_per_unit")
        except Exception:
            pass

    items = []
    if price_single is not None and price_single > 0:
        items.append({
            "name": title[:500],
            "brand": BRAND_NAME,
            "category": category_label,
            "price": round(price_single, 2),
            "currency": "USD",
            "url": url,
            "base_url": BASE_URL,
        })
    if price_2pack is not None and price_2pack > 0:
        items.append({
            "name": f"{title} — 2 Pack"[:500],
            "brand": BRAND_NAME,
            "category": category_label,
            "price": round(price_2pack, 2),
            "currency": "USD",
            "url": f"{url}&v=2pack" if "?" in url else f"{url}?v=2pack",
            "base_url": BASE_URL,
        })
    return items


@register("shapermint_store")
def scrape_shapermint_store() -> list[dict]:
    """Scrape shapermint.com via vision only (screenshot + AI)."""
    all_items = []
    for category_label, product_path in SHAPERMINT_STORE_PRODUCTS:
        try:
            items = _scrape_product_page(category_label, product_path)
            all_items.extend(items)
        except Exception as e:
            raise RuntimeError(f"Shapermint Store ({category_label}) {product_path}: {e}") from e
        time.sleep(config.REQUEST_DELAY_SECONDS)
    return all_items
