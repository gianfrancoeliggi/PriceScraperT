"""Run the scraper once and save to the DB (uses .streamlit/secrets.toml for DATABASE_URL)."""
import os
import re

# Load .streamlit/secrets.toml and set DATABASE_URL
secrets_path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
if os.path.exists(secrets_path):
    with open(secrets_path) as f:
        for line in f:
            m = re.match(r'DATABASE_URL\s*=\s*["\']([^"\']+)["\']', line.strip())
            if m:
                os.environ["DATABASE_URL"] = m.group(1)
                break

from db import init_db
from scrapers import run_all_scrapers

if __name__ == "__main__":
    init_db()
    result = run_all_scrapers(save=True)
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
