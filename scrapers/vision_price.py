"""
Extract product prices from a page screenshot using a vision AI.
Supports OpenAI (GPT-4o-mini) or Anthropic (Claude). Use ANTHROPIC_API_KEY or OPENAI_API_KEY in secrets.
"""
import base64
import json
import os
import re


def _call_vision_api(image_png_bytes: bytes, prompt: str) -> str:
    """Call OpenAI or Anthropic vision API; return response text. Prefers Anthropic if ANTHROPIC_API_KEY is set."""
    b64 = base64.b64encode(image_png_bytes).decode("ascii")
    api_key_anthropic = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    api_key_openai = os.environ.get("OPENAI_API_KEY", "").strip()

    if api_key_anthropic:
        try:
            from anthropic import Anthropic
        except ImportError:
            raise RuntimeError("anthropic package required. Install: pip install anthropic")
        client = Anthropic(api_key=api_key_anthropic)
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=200,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": "image/png", "data": b64},
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        text = (response.content[0].text if response.content else "") or ""
        return text.strip()

    if api_key_openai:
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("openai package required. Install: pip install openai")
        client = OpenAI(api_key=api_key_openai)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    ],
                }
            ],
            max_tokens=200,
        )
        return (response.choices[0].message.content or "").strip()

    raise RuntimeError(
        "Set ANTHROPIC_API_KEY or OPENAI_API_KEY in env or .streamlit/secrets.toml for vision price extraction."
    )


def extract_prices_from_image(image_png_bytes: bytes) -> dict:
    """
    Send screenshot to vision API (Claude or OpenAI) and get structured prices for Store.
    Returns {"price_single": float or None, "price_2pack_per_unit": float or None}.
    """
    prompt = """You are looking at a product page screenshot (e.g. Shapermint store).

Extract ONLY the actual selling prices in USD:
1) The main price for buying 1 unit (the price the customer pays for one item). Ignore "Compare at", "Save $X", "X% off" — those are not the selling price.
2) If there is a "Get 2 for" or "2-pack" offer, the price PER UNIT for that offer (e.g. if it says "2 for $29.99 each" return 29.99; if "2 for $59.98" return 29.99 as per unit).

Reply with a single JSON object, nothing else:
{"price_single": 37.99, "price_2pack_per_unit": 29.99}
Use null for any value you cannot see (e.g. no 2-pack offer: "price_2pack_per_unit": null).
Only numbers that are clearly the product's selling price. Do not use "Save $X" or discount amounts as prices."""

    text = _call_vision_api(image_png_bytes, prompt)
    json_match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if not json_match:
        return {"price_single": None, "price_2pack_per_unit": None}
    try:
        data = json.loads(json_match.group())
        single = data.get("price_single")
        two = data.get("price_2pack_per_unit")
        if single is not None and not isinstance(single, (int, float)):
            single = None
        if two is not None and not isinstance(two, (int, float)):
            two = None
        return {
            "price_single": float(single) if single is not None else None,
            "price_2pack_per_unit": float(two) if two is not None else None,
        }
    except (json.JSONDecodeError, TypeError, ValueError):
        return {"price_single": None, "price_2pack_per_unit": None}


def extract_amazon_prices_from_image(image_png_bytes: bytes) -> list[float]:
    """
    Send Amazon product page screenshot to vision API; return list of distinct selling prices in USD.
    """
    prompt = """You are looking at an Amazon product page screenshot.

Extract ALL distinct product selling prices shown in USD (the main price and any variant prices for different colors/packs).
Ignore: "Save $X", "X% off", discount amounts, shipping, taxes, and any number that is not a product price.
Only include the actual price(s) the customer pays (e.g. 39.99, 40.99).

Reply with a single JSON object, nothing else:
{"prices": [39.99, 40.99]}
Use an empty array if you see no clear price. Use "prices": [39.99] for a single price."""

    text = _call_vision_api(image_png_bytes, prompt)
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if not json_match:
        arr_m = re.search(r'"prices"\s*:\s*\[([^\]]*)\]', text)
        if arr_m:
            try:
                arr = json.loads("[" + arr_m.group(1) + "]")
                return [round(float(x), 2) for x in arr if isinstance(x, (int, float)) and 5 <= float(x) <= 500]
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
        return []
    try:
        data = json.loads(json_match.group())
        raw = data.get("prices")
        if not isinstance(raw, list):
            return []
        return [round(float(x), 2) for x in raw if isinstance(x, (int, float)) and 5 <= float(x) <= 500]
    except (json.JSONDecodeError, TypeError, ValueError):
        return []
