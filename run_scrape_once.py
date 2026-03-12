"""Run the scraper once and save to the DB (uses .streamlit/secrets.toml for DATABASE_URL, OPENAI_API_KEY)."""
import os
import re

# Load .streamlit/secrets.toml into os.environ
secrets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".streamlit", "secrets.toml")
if os.path.exists(secrets_path):
    with open(secrets_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip().lstrip("\ufeff")
            if not line or line.startswith("#"):
                continue
            m = re.match(r'(\w+)\s*=\s*["\']([^"\']*)["\']', line)
            if m:
                key, val = m.group(1), m.group(2)
                if key in (
                    "DATABASE_URL", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "USE_VISION_PRICES",
                    "AMAZON_PROXY_URL", "AMAZON_PROXY_USER", "AMAZON_PROXY_PASSWORD",
                    "HTTP_PROXY", "HTTPS_PROXY",
                ):
                    os.environ[key] = val
                elif key.upper() == "OPENAI_API_KEY":
                    os.environ["OPENAI_API_KEY"] = val
                elif key.upper() == "ANTHROPIC_API_KEY":
                    os.environ["ANTHROPIC_API_KEY"] = val
            else:
                m2 = re.match(r'OPENAI_API_KEY\s*=\s*(\S+)', line, re.IGNORECASE)
                if m2:
                    os.environ["OPENAI_API_KEY"] = m2.group(1).strip('"\'')
                m3 = re.match(r'ANTHROPIC_API_KEY\s*=\s*(\S+)', line, re.IGNORECASE)
                if m3:
                    os.environ["ANTHROPIC_API_KEY"] = m3.group(1).strip('"\'')
    if not os.environ.get("OPENAI_API_KEY") and not os.environ.get("ANTHROPIC_API_KEY"):
        print("Note: Set OPENAI_API_KEY or ANTHROPIC_API_KEY in secrets.toml for Shapermint vision.")

from db import init_db
from scrapers import run_all_scrapers

# By default run only Shapermint Amazon. Set RUN_ALL_SCRAPERS=1 to run all brands.
# Set RUN_AMAZON_AND_STORE=1 to run only Shapermint Amazon + Shapermint Store.
ONLY_AMAZON = not (os.environ.get("RUN_ALL_SCRAPERS", "").strip().lower() in ("1", "true", "yes"))
AMAZON_AND_STORE = os.environ.get("RUN_AMAZON_AND_STORE", "").strip().lower() in ("1", "true", "yes")

if __name__ == "__main__":
    init_db()
    if AMAZON_AND_STORE:
        only_brands = ["shapermint", "shapermint_store"]
        print("Running Shapermint Amazon and Shapermint Store.")
    elif ONLY_AMAZON:
        only_brands = ["shapermint"]
        print("Running only Shapermint Amazon. Set RUN_ALL_SCRAPERS=1 to run all scrapers.")
    else:
        only_brands = None
    result = run_all_scrapers(save=True, only_brands=only_brands)
    items = result["items"]
    products_updated = result["products_updated"]
    price_records = result["price_records_inserted"]
    per_brand = result["per_brand"]
    print(f"Done. Items: {len(items)}, products updated: {products_updated}, price records: {price_records}")
    for brand, (count, err) in per_brand.items():
        if err:
            print(f"  {brand}: {err}")
        else:
            print(f"  {brand}: {count} items")
