"""Shapermint products on Amazon — HTML parsing: click each variant radio, read price from span[aria-hidden='true']."""
import time
from urllib.parse import urljoin

from bs4 import BeautifulSoup

import config
from scrapers.base import register, clean_product_name
from scrapers.browser import get_page_html, get_amazon_variant_prices

BRAND_NAME = "Shapermint Amazon"
BASE_URL = "https://www.amazon.com"

# Only persist prices in this range (reject IDs / wrong locale)
_AMAZON_PRICE_MIN, _AMAZON_PRICE_MAX = 5.0, 500.0

SHAPERMINT_AMAZON_PRODUCTS = [
    ("EBRA", "https://www.amazon.com/SHAPERMINT-Bras-Women-Bralettes-Lingerie/dp/B0D9YHD4C1"),
    ("STBRA", "https://www.amazon.com/SHAPERMINT-Convertible-Strapless-Bras-Women/dp/B0CG7L63JZ"),
    ("CAMI", "https://www.amazon.com/SHAPERMINT-Womens-Tops-Camisole-Shapewear/dp/B0C47L679F"),
    ("Sweetheart BRA", "https://www.amazon.com/SHAPERMINT-Sweetheart-Bras-Women-Comfortable/dp/B0F8WBMWBR"),
    ("Tank CAMI", "https://www.amazon.com/SHAPERMINT-Womens-Tops-Shapewear-Camisole/dp/B07NNVRMGR"),
    ("BRAHE", "https://www.amazon.com/SHAPERMINT-Compression-Wirefree-Everyday-Exercise/dp/B0C3HCF5JK"),
    ("BSS", "https://www.amazon.com/EMPETUA-Shapermint-High-Waisted-Shaper-Shorts/dp/B07QRG7PBV"),
]


def _normalize_url(url: str) -> str:
    return url.split("?")[0].rstrip("/") if url and url.startswith("http") else urljoin(BASE_URL, url).split("?")[0].rstrip("/")


def _url_with_currency_usd(url: str) -> str:
    """Append currency=USD so Amazon may show USD prices (avoids ARS when geo is non-US)."""
    if not url:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url.rstrip('/')}{sep}currency=USD"


def _get_title_from_html(url: str) -> str:
    try:
        html = get_page_html(url, wait_selector="#productTitle, #title, .a-price")
    except Exception:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for sel in ["#productTitle", "#title", "h1[id*='title']"]:
        el = soup.select_one(sel)
        if el:
            t = (el.get_text(strip=True) or "").strip()
            if t:
                return clean_product_name(t)
    return ""


def _scrape_product_page(category_label: str, product_url: str) -> list[dict]:
    """Load page, click each variant radio (name=0,1,2,...), collect prices from span[aria-hidden='true']."""
    norm_url = _normalize_url(product_url)
    url_for_fetch = _url_with_currency_usd(product_url)
    title = _get_title_from_html(url_for_fetch) or f"Shapermint {category_label}"
    prices = get_amazon_variant_prices(url_for_fetch)
    if not prices:
        prices = []

    # Only keep prices in valid range (never persist 56,615 etc.)
    prices = [round(p, 2) for p in prices if _AMAZON_PRICE_MIN <= p <= _AMAZON_PRICE_MAX]
    items = []
    for i, price in enumerate(prices):
        if price <= 0:
            continue
        variant = f" — Option {i + 1}" if len(prices) > 1 else ""
        item_url = f"{norm_url}?v=opt{i + 1}" if len(prices) > 1 else norm_url
        items.append({
            "name": (title + variant)[:500],
            "brand": BRAND_NAME,
            "category": category_label,
            "price": round(price, 2),
            "currency": "USD",
            "url": item_url,
            "base_url": BASE_URL,
        })
    return items


@register("shapermint")
def scrape_shapermint_amazon() -> list[dict]:
    """Scrape Shapermint Amazon via HTML: click variant radios, read prices from span[aria-hidden='true']."""
    all_items = []
    for category_label, product_url in SHAPERMINT_AMAZON_PRODUCTS:
        try:
            items = _scrape_product_page(category_label, product_url)
            all_items.extend(items)
        except Exception as e:
            raise RuntimeError(f"Shapermint Amazon ({category_label}) {product_url}: {e}") from e
        time.sleep(config.REQUEST_DELAY_SECONDS)
    return all_items
