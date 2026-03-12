"""Optional browser-based fetching for JS-rendered pages."""
import os
import re
import time
from typing import List, Optional

import config

DEBUG_AMAZON = os.environ.get("DEBUG_AMAZON_SCRAPER", "").strip().lower() in ("1", "true", "yes")


def _get_amazon_proxy_config() -> Optional[dict]:
    """
    Build Playwright proxy dict from env. Precedence: AMAZON_PROXY_URL, then HTTPS_PROXY, then HTTP_PROXY.
    Optional auth: AMAZON_PROXY_USER, AMAZON_PROXY_PASSWORD (or user:pass in URL).
    Returns None if no proxy configured.
    """
    url = (
        os.environ.get("AMAZON_PROXY_URL")
        or os.environ.get("HTTPS_PROXY")
        or os.environ.get("HTTP_PROXY")
    )
    if not url or not url.strip():
        return None
    url = url.strip()
    if not re.match(r"^[\w+.-]+://", url):
        url = "http://" + url
    # Split server (no credentials) and optional user/pass from URL
    server = url
    username = os.environ.get("AMAZON_PROXY_USER", "").strip()
    password = os.environ.get("AMAZON_PROXY_PASSWORD", "").strip()
    m = re.match(r"^([\w+.-]+://)([^@]+)@(.+)$", url)
    if m:
        prefix, user_pass, rest = m.group(1), m.group(2), m.group(3)
        server = prefix + rest
        if not username and not password and ":" in user_pass:
            username, password = user_pass.split(":", 1)
        elif not username:
            username = user_pass
    out = {"server": server}
    if username or password:
        out["username"] = username
        out["password"] = password
    return out


def get_page_screenshot(
    url: str,
    wait_selector: Optional[str] = None,
    element_selector: Optional[str] = None,
) -> bytes:
    """
    Load URL with Playwright and return PNG screenshot as bytes.
    If element_selector is set, screenshot only that element (e.g. price block).
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError(
            "Playwright required. Install: pip install playwright && playwright install chromium"
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
            if element_selector:
                try:
                    loc = page.locator(element_selector).first
                    loc.wait_for(state="visible", timeout=5000)
                    return loc.screenshot(type="png")
                except Exception:
                    pass
            return page.screenshot(type="png", full_page=False)
        finally:
            browser.close()


# When Amazon shows ARS (e.g. from Argentina IP), convert to USD. Rate = USD per 1 ARS (e.g. ~0.001).
_ARS_TO_USD_RATE = float(os.environ.get("ARS_TO_USD_RATE", "0.001"))


def _parse_price_from_text(text: str) -> Optional[float]:
    """Extract price from '$37.99' or '37.99'; return None if not in 5-500 range."""
    if not text:
        return None
    m = re.search(r"[\d,]+\.?\d*", str(text).strip().replace(",", ""))
    if m:
        v = float(m.group().replace(",", ""))
        return v if 5 <= v <= 500 else None
    return None


def _parse_ars_and_convert_to_usd(text: str) -> Optional[float]:
    """If text is like 'ARS74,159.50', extract number, convert to USD, return if in 5-500."""
    if not text or "ARS" not in text.upper():
        return None
    m = re.search(r"[\d,]+\.?\d*", str(text).strip().replace(",", ""))
    if not m:
        return None
    ars = float(m.group().replace(",", ""))
    usd = round(ars * _ARS_TO_USD_RATE, 2)
    return usd if 5 <= usd <= 500 else None


def _get_one_price_from_page(page, use_ars_fallback: bool = True) -> Optional[float]:
    """Try all known price selectors on the page; return one valid price in 5–500 range or None."""
    # 1) span[aria-hidden="true"] with $XX.XX
    for sel in ["#corePrice_feature_div", "#corePriceDisplay_desktop_feature_div", "#apex_desktop", "body"]:
        for span in page.locator(f"{sel} span[aria-hidden='true']").all():
            try:
                text = span.inner_text().strip()
                if re.match(r"^\$[\d,]+\.?\d*$", text):
                    p = _parse_price_from_text(text)
                    if p is not None:
                        return round(p, 2)
            except Exception:
                continue
    # 2) .a-price-whole + .a-price-fraction
    p = _get_price_from_whole_fraction(page, use_ars_fallback=use_ars_fallback)
    if p is not None:
        return p
    # 3) .a-price .a-offscreen
    for sel in ["#corePrice_feature_div", "#corePriceDisplay_desktop_feature_div", "#apex_desktop", "body"]:
        for el in page.locator(f"{sel} .a-price .a-offscreen").all():
            try:
                raw = el.inner_text().strip()
                p = _parse_price_from_text(raw)
                if p is not None:
                    return round(p, 2)
                if use_ars_fallback:
                    p = _parse_ars_and_convert_to_usd(raw)
                    if p is not None:
                        return round(p, 2)
            except Exception:
                continue
    return None


def _get_price_from_whole_fraction(page, use_ars_fallback: bool = True) -> Optional[float]:
    """
    Amazon sometimes shows price as .a-price-whole (e.g. 37) + .a-price-fraction (e.g. 99).
    Search in buybox first, then page. Returns parsed price in 5–500 range or None.
    """
    def in_scope(selector: str):
        return page.locator(selector)

    for scope_sel in [
        "#corePrice_feature_div .a-price",
        "#corePriceDisplay_desktop_feature_div .a-price",
        "#apex_desktop .a-price",
        ".a-price",
    ]:
        for box in in_scope(scope_sel).all():
            try:
                whole_el = box.locator(".a-price-whole").first
                frac_el = box.locator(".a-price-fraction").first
                if whole_el.count() and frac_el.count():
                    whole_t = re.sub(r"[^\d]", "", whole_el.inner_text().strip())
                    frac_t = frac_el.inner_text().strip()
                    if whole_t and frac_t:
                        combined = f"{whole_t}.{frac_t}"
                        p = _parse_price_from_text(combined)
                        if p is not None:
                            return round(p, 2)
                        if use_ars_fallback:
                            try:
                                val = float(combined)
                                if val > 500:
                                    usd = round(val * _ARS_TO_USD_RATE, 2)
                                    if 5 <= usd <= 500:
                                        return usd
                            except ValueError:
                                pass
            except Exception:
                continue
    return None


def _set_amazon_delivery_zip(page, zip_code: str = "33101") -> None:
    """
    On current Amazon page: click "Deliver to", enter US zip (e.g. 33101 Miami),
    submit so Amazon shows USD. No-op if elements are missing.
    """
    try:
        # Click "Deliver to" to open the location modal
        deliver_to = page.locator("#glow-ingress-line2").first
        if deliver_to.count() == 0:
            return
        deliver_to.click(force=True, timeout=5000)
        time.sleep(1)
        # Wait for zip input and fill it
        zip_input = page.locator("#GLUXZipUpdateInput").first
        zip_input.wait_for(state="visible", timeout=5000)
        zip_input.fill(zip_code)
        time.sleep(0.5)
        # Click submit (Apply/Done)
        submit_btn = page.locator('input.a-button-input[type="submit"][aria-labelledby="GLUXZipUpdate-announce"]').first
        if submit_btn.count() > 0:
            submit_btn.click(force=True, timeout=5000)
            time.sleep(6)
    except Exception:
        pass


def get_amazon_variant_prices(url: str) -> List[float]:
    """
    Load Amazon PDP, set delivery zip to 33101 (Miami) so prices show in USD, then click each
    variant radio (input name="0", "1", ...), read price from span[aria-hidden="true"] or
    .a-price-whole + .a-price-fraction.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError("Playwright required. Install: pip install playwright && playwright install chromium")
    proxy_config = _get_amazon_proxy_config()
    use_ars_fallback = proxy_config is None
    if DEBUG_AMAZON and proxy_config:
        print(f"[DEBUG] Using proxy: {proxy_config.get('server', '')}")
    prices: List[float] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            kwargs = {
                "locale": "en-US",
                "timezone_id": "America/New_York",
                "extra_http_headers": {
                    "User-Agent": config.USER_AGENT,
                    "Accept-Language": "en-US,en;q=0.9",
                },
            }
            if proxy_config:
                kwargs["proxy"] = proxy_config
            context = browser.new_context(**kwargs)
            page = context.new_page()
            if DEBUG_AMAZON:
                print(f"[DEBUG] Loading {url[:80]}...")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(1)
            # Set delivery to US zip (33101 Miami) so Amazon shows USD
            _set_amazon_delivery_zip(page, "33101")
            # Wait for variant buttons or price to be present (some pages load late)
            waited = None
            for selector in [
                "input[name='0'][role='radio']",
                "input.a-button-input[role='radio']",
                ".a-price",
                "span[aria-hidden='true']",
            ]:
                try:
                    page.wait_for_selector(selector, timeout=10000)
                    waited = selector
                    break
                except Exception as e:
                    if DEBUG_AMAZON:
                        print(f"[DEBUG] wait_for_selector({selector!r}) failed: {e}")
                    continue
            if DEBUG_AMAZON:
                print(f"[DEBUG] Waited for: {waited}")
            time.sleep(2)
            n = 0
            while True:
                # Match exact user spec: input name="0", "1", ... role=radio class=a-button-input
                variant_loc = page.locator(f"input[name='{n}'][role='radio'].a-button-input")
                try:
                    cnt = variant_loc.count()
                except Exception as e:
                    if DEBUG_AMAZON:
                        print(f"[DEBUG] variant n={n} count() failed: {e}")
                    break
                if DEBUG_AMAZON:
                    print(f"[DEBUG] variant n={n} count={cnt}")
                if cnt == 0:
                    # No more variants: if we have no prices yet, try once to get at least one price from page
                    if not prices:
                        p = _get_one_price_from_page(page, use_ars_fallback=use_ars_fallback)
                        if DEBUG_AMAZON:
                            print(f"[DEBUG] fallback single price: {p}")
                        if p is not None:
                            prices.append(p)
                    break
                if n > 0:
                    try:
                        variant_loc.first.click(force=True, timeout=5000)
                        time.sleep(1.5)
                    except Exception as e:
                        if DEBUG_AMAZON:
                            print(f"[DEBUG] click n={n} failed: {e}")
                        n += 1
                        continue
                p = _get_one_price_from_page(page, use_ars_fallback=use_ars_fallback)
                if p is None and n == 0:
                    time.sleep(2)
                    p = _get_one_price_from_page(page, use_ars_fallback=use_ars_fallback)
                if DEBUG_AMAZON:
                    print(f"[DEBUG] variant n={n} price={p}")
                if p is not None:
                    prices.append(p)
                n += 1
                if n > 50:
                    break
        finally:
            browser.close()
    if DEBUG_AMAZON:
        print(f"[DEBUG] URL done, total prices: {len(prices)} {prices}")
    return prices


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
