"""Honeylove shapewear scraper (uses Playwright for consistent product HTML)."""
import re
import time
from typing import Optional

from bs4 import BeautifulSoup

import config
from scrapers.base import register, clean_product_name
from scrapers.browser import get_page_html

BRAND_NAME = "Honeylove"
BASE_URL = "https://www.honeylove.com"


def _parse_price(s: str) -> Optional[float]:
    if not s:
        return None
    s = s.strip().replace(",", ".")
    match = re.search(r"[\d]+\.?\d*", s)
    if match:
        return float(match.group())
    return None


def _get_currency(s: str) -> str:
    if "$" in s or "USD" in s.upper():
        return "USD"
    if "£" in s or "GBP" in s.upper():
        return "GBP"
    if "€" in s or "EUR" in s.upper():
        return "EUR"
    return "USD"


@register("honeylove")
def scrape_honeylove() -> list[dict]:
    """Scrape Honeylove shapewear collection. Returns list of product dicts."""
    items = []
    url = config.HONEYLOVE_SHAPEWEAR_URL
    try:
        html = get_page_html(url, wait_selector='a[href*="/products/"]')
        soup = BeautifulSoup(html, "html.parser")
        product_links = soup.select('a[href*="/products/"]')
        seen_urls = set()
        for a in product_links:
            href = a.get("href", "")
            if "?" in href:
                href = href.split("?")[0]
            if not href.startswith("http"):
                href = BASE_URL + href if href.startswith("/") else BASE_URL + "/" + href
            if href in seen_urls:
                continue
            seen_urls.add(href)
            name = (a.get_text(strip=True) or a.get("aria-label") or "").strip()
            name = re.sub(r"\$[\d,]+\.?\d*|£[\d,]+\.?\d*|€[\d,]+\.?\d*|[\d,]+\.?\d*\s*€", "", name).strip()
            name = clean_product_name(name)
            if not name:
                name = href.rstrip("/").split("/")[-1].replace("-", " ").title()
            parent = a.find_parent(["div", "li", "article", "section"])
            price_val = None
            currency = "USD"
            for _ in range(5):
                if not parent:
                    break
                price_el = parent.find(class_=re.compile(r"price|money|product.*price", re.I))
                if price_el:
                    price_text = price_el.get_text(strip=True)
                    price_val = _parse_price(price_text)
                    if price_val is not None:
                        currency = _get_currency(price_text)
                        break
                for t in parent.find_all(string=re.compile(r"[\$£€]\s*[\d,]+\.?\d*|[\d,]+\.?\d*\s*[€]")):
                    price_val = _parse_price(t)
                    if price_val is not None:
                        currency = _get_currency(t)
                        break
                if price_val is not None:
                    break
                parent = parent.find_parent(["div", "li", "article", "section"])
            if price_val is None:
                price_val = _parse_price(a.get_text())
                if price_val is not None:
                    currency = _get_currency(a.get_text())
            items.append({
                "name": name or "Unknown",
                "brand": BRAND_NAME,
                "category": "shapewear",
                "price": price_val,
                "currency": currency,
                "url": href,
                "base_url": BASE_URL,
            })
        time.sleep(config.REQUEST_DELAY_SECONDS)
    except Exception as e:
        raise RuntimeError(f"Honeylove request failed for {url}: {e}") from e
    return items
