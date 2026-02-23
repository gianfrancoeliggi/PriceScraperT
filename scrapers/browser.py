"""Optional browser-based fetching for JS-rendered pages."""
import time
from typing import Optional

import config


def get_page_html(url: str, wait_selector: Optional[str] = None) -> str:
    """
    Fetch URL with Playwright (headless) and return rendered HTML.
    If wait_selector is set, wait for that selector before getting content.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError(
            "Playwright is required for this scraper. Install with: pip install playwright && playwright install chromium"
        )
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_extra_http_headers({"User-Agent": config.USER_AGENT})
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            if wait_selector:
                try:
                    page.wait_for_selector(wait_selector, timeout=15000)
                except Exception:
                    pass
            time.sleep(2)
            html = page.content()
            return html
        finally:
            browser.close()
