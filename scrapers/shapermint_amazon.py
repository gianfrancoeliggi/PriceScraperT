"""Shapermint products on Amazon — one URL per product page; full title and ALL price variants (color, pack, etc.)."""
import re
import time
import unicodedata
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

import config
from scrapers.base import register, clean_product_name
from scrapers.browser import get_page_html

BRAND_NAME = "Shapermint Amazon"
BASE_URL = "https://www.amazon.com"

# Consolidated: one URL per category (EBRA, STBRA, CAMI, etc.); each page may have multiple price variants (color, pack).
SHAPERMINT_AMAZON_PRODUCTS = [
    ("EBRA", "https://www.amazon.com/SHAPERMINT-Bras-Women-Bralettes-Lingerie/dp/B0D9YHD4C1"),
    ("STBRA", "https://www.amazon.com/SHAPERMINT-Convertible-Strapless-Bras-Women/dp/B0CG7L63JZ"),
    ("CAMI", "https://www.amazon.com/SHAPERMINT-Womens-Tops-Camisole-Shapewear/dp/B0C47L679F"),
    ("Sweetheart BRA", "https://www.amazon.com/SHAPERMINT-Sweetheart-Bras-Women-Comfortable/dp/B0F8WBMWBR"),
    ("Tank CAMI", "https://www.amazon.com/SHAPERMINT-Womens-Tops-Shapewear-Camisole/dp/B07NNVRMGR"),
    ("BRAHE", "https://www.amazon.com/SHAPERMINT-Compression-Wirefree-Everyday-Exercise/dp/B0C3HCF5JK"),
    ("BSS", "https://www.amazon.com/EMPETUA-Shapermint-High-Waisted-Shaper-Shorts/dp/B07QRG7PBV"),
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


def _normalize_url(url: str) -> str:
    """Canonical product URL (no query string) for same-product grouping; use full url for variants."""
    if not url or not url.startswith("http"):
        url = urljoin(BASE_URL, url)
    return url.split("?")[0].rstrip("/")


def _slug(variant: str) -> str:
    """Short slug for variant to use in ?v= query (unique per price variant)."""
    if not variant:
        return "default"
    s = re.sub(r"[^a-z0-9]+", "-", variant.lower().strip())
    return (s[:50] or "v").strip("-")


def _extract_title(soup: BeautifulSoup) -> str:
    """Full product title from Amazon product page."""
    # #productTitle is the main one on PDP
    el = soup.select_one("#productTitle")
    if el:
        title = (el.get_text(strip=True) or "").strip()
        if title:
            return clean_product_name(title)
    el = soup.select_one("#title")
    if el:
        title = (el.get_text(strip=True) or "").strip()
        if title:
            return clean_product_name(title)
    h1 = soup.select_one("h1[id*='title'], h1.a-size-large")
    if h1:
        title = (h1.get_text(strip=True) or "").strip()
        if title:
            return clean_product_name(title)
    return ""


def _extract_prices_from_dom(soup: BeautifulSoup) -> list[tuple[str, float]]:
    """Find all (variant_label, price) from DOM: main buybox + variant rows (color/size/pack)."""
    out: list[tuple[str, float]] = []
    seen: set[tuple[str, float]] = set()

    def add(variant: str, price: float):
        key = (variant.strip(), round(price, 2))
        if key not in seen and price > 0:
            seen.add(key)
            out.append((variant.strip(), round(price, 2)))

    # 1) Main buybox / above-the-fold price
    for sel in [".a-price .a-offscreen", ".a-price .a-offscreen", "#priceblock_ourprice", "#priceblock_dealprice", "#priceblock_saleprice"]:
        for el in soup.select(sel):
            t = el.get_text(strip=True)
            p = _parse_price(t)
            if p is not None:
                add("", p)
                break
        if out:
            break

    # 2) .a-price-whole + .a-price-fraction (main price)
    price_box = soup.select_one("#corePrice_feature_div, #corePriceDisplay_desktop_feature_div, #apex_desktop")
    if price_box:
        whole = price_box.select_one(".a-price-whole")
        frac = price_box.select_one(".a-price-fraction")
        if whole:
            w = whole.get_text(strip=True).replace(",", "")
            f = frac.get_text(strip=True) if frac else "0"
            p = _parse_price(f"{w}.{f}")
            if p is not None:
                add("", p)

    # 3) Twister (variation) rows: color, size, pack — each can have a different price
    for row in soup.select(
        "[data-feature-name='twisterContainer'] li, .po-variant .po-variant-row, "
        "[data-csa-c-type='element'], li[data-asin], .a-section .a-row[data-csa-c-type='element']"
    ):
        variant_parts = []
        for label in row.select(".po-variant-name span, .a-form-label, [data-csa-c-id] span, .a-text-left"):
            v = label.get_text(strip=True)
            if v and not re.match(r"^\$[\d.]+$", v) and len(v) < 100:
                variant_parts.append(v)
        variant = " ".join(variant_parts).strip() if variant_parts else ""
        price_el = row.select_one(".a-price .a-offscreen, .a-price-whole")
        if price_el:
            if "a-offscreen" in (price_el.get("class") or []):
                p = _parse_price(price_el.get_text(strip=True))
            else:
                whole = row.select_one(".a-price-whole")
                frac = row.select_one(".a-price-fraction")
                if whole:
                    w = whole.get_text(strip=True).replace(",", "")
                    f = frac.get_text(strip=True) if frac else "0"
                    p = _parse_price(f"{w}.{f}")
                else:
                    p = _parse_price(price_el.get_text(strip=True))
            if p is not None:
                add(variant, p)
        # Row text: "1 Pack, Black — $25.99" style
        text = row.get_text(strip=True)
        price_in_text = re.search(r"\$[\d,]+\.?\d*", text)
        if price_in_text:
            p = _parse_price(price_in_text.group())
            if p is not None:
                variant_from_text = re.sub(r"\$[\d,]+\.?\d*", "", text).strip()
                variant_from_text = re.sub(r"\s+", " ", variant_from_text)[:80]
                add(variant or variant_from_text, p)

    # 4) All .a-price on page (catch any we missed)
    for el in soup.select(".a-price .a-offscreen"):
        t = el.get_text(strip=True)
        p = _parse_price(t)
        if p is not None:
            add("", p)

    # 5) JSON in script tags (Amazon embeds priceAmount / displayPrice)
    for script in soup.select("script:not([src])"):
        txt = script.get_text() or ""
        for m in re.finditer(r'"priceAmount"\s*:\s*([\d.]+)', txt):
            p = float(m.group(1))
            if p > 0:
                add("", p)
        for m in re.finditer(r'"displayPrice"\s*:\s*"\$?([\d,.]+)"', txt):
            p = _parse_price(m.group(1))
            if p is not None:
                add("", p)

    return out


def _scrape_product_page(category_label: str, product_url: str) -> list[dict]:
    """Load one Amazon product page; return list of items (one per price variant): full name + variant, price USD."""
    norm_url = _normalize_url(product_url)
    try:
        html = get_page_html(product_url, wait_selector="#productTitle, #title, .a-price, #corePrice_feature_div")
    except Exception as e:
        raise RuntimeError(f"Shapermint Amazon fetch failed {product_url}: {e}") from e

    soup = BeautifulSoup(html, "html.parser")
    title = _extract_title(soup)
    if not title:
        # Fallback from URL slug (e.g. SHAPERMINT-Bodysuit-Shapewear-Control -> Shapermint Bodysuit Shapewear Control)
        slug = norm_url.split("/dp/")[-1].split("/")[0] if "/dp/" in norm_url else ""
        if slug:
            title = clean_product_name(slug.replace("-", " "))

    if not title:
        title = f"Shapermint {category_label}"

    price_variants = _extract_prices_from_dom(soup)
    if not price_variants:
        # Fallback: any $XX.XX on the page
        for m in re.finditer(r"\$[\s]*([\d,]+\.?\d*)", soup.get_text()):
            p = _parse_price(m.group(1))
            if p is not None and p > 0:
                price_variants.append(("", p))
                break

    items = []
    for variant_label, price in price_variants:
        if price <= 0:
            continue
        display_name = f"{title} — {variant_label}" if variant_label else title
        display_name = clean_product_name(display_name)[:500]
        # Unique URL per variant so DB stores each price as separate product
        item_url = norm_url if not variant_label else f"{norm_url}?v={_slug(variant_label)}"
        items.append({
            "name": display_name,
            "brand": BRAND_NAME,
            "category": category_label,
            "price": price,
            "currency": "USD",
            "url": item_url,
            "base_url": BASE_URL,
        })
    return items


@register("shapermint")
def scrape_shapermint_amazon() -> list[dict]:
    """Scrape each Shapermint product page (one URL per category); return all products with ALL price variants (color, pack, etc.)."""
    all_items = []
    for category_label, product_url in SHAPERMINT_AMAZON_PRODUCTS:
        try:
            items = _scrape_product_page(category_label, product_url)
            all_items.extend(items)
        except Exception as e:
            raise RuntimeError(f"Shapermint Amazon ({category_label}) {product_url}: {e}") from e
        time.sleep(config.REQUEST_DELAY_SECONDS)
    return all_items
