"""Spanx shapewear scraper."""
import re
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup

import config
from scrapers.base import register, clean_product_name

BRAND_NAME = "Spanx"
BASE_URL = "https://www.spanx.com"


def _parse_price(s: str) -> Optional[float]:
    """Extract numeric price from string like '£99.00', '$49.00', '115,00 €'."""
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


def _scrape_collection(url: str, category: str) -> list[dict]:
    headers = {"User-Agent": config.USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}
    items = []
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        # Shopify-style: product cards often in a grid; links to /products/
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
            # Product name: use link text or title, clean up
            name = (a.get_text(strip=True) or a.get("aria-label") or "").strip()
            # Remove price from name if it got included (e.g. "Product Name $99.00")
            name = re.sub(r"\$[\d,]+\.?\d*|£[\d,]+\.?\d*|[\d,]+\.?\d*\s*€", "", name).strip()
            name = clean_product_name(name)
            if not name:
                name = href.rstrip("/").split("/")[-1].replace("-", " ").title()
            # Find price in same card: go up to a common parent then search for price
            parent = a.find_parent(["div", "li", "article"])
            price_val = None
            currency = "USD"
            if parent:
                price_el = parent.find(class_=re.compile(r"price|money", re.I))
                if price_el:
                    price_text = price_el.get_text(strip=True)
                    price_val = _parse_price(price_text)
                    currency = _get_currency(price_text)
                if price_val is None:
                    for t in parent.find_all(string=re.compile(r"\$|£|€|USD|GBP|EUR")):
                        price_val = _parse_price(t)
                        if price_val is not None:
                            currency = _get_currency(t)
                            break
            if price_val is None:
                # Fallback: any price in the link text
                price_val = _parse_price(a.get_text())
                if price_val is not None:
                    currency = _get_currency(a.get_text())
            items.append({
                "name": name or "Unknown",
                "brand": BRAND_NAME,
                "category": category or "shapewear",
                "price": price_val,
                "currency": currency,
                "url": href,
                "base_url": BASE_URL,
            })
        time.sleep(config.REQUEST_DELAY_SECONDS)
    except requests.RequestException as e:
        raise RuntimeError(f"Spanx request failed for {url}: {e}") from e
    return items


@register("spanx")
def scrape_spanx() -> list[dict]:
    """Scrape Spanx shapewear collections. Returns list of product dicts."""
    all_items = []
    for url in config.SPANX_COLLECTIONS:
        category = url.rstrip("/").split("/")[-1].replace("-", " ").title()
        all_items.extend(_scrape_collection(url, category))
        time.sleep(config.REQUEST_DELAY_SECONDS)
    return all_items
