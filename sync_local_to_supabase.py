"""
Copy data from local SQLite (data/prices.db) to Supabase.
Run this when you have network access so the public app shows your local data.

Usage:
  python3 sync_local_to_supabase.py

If you get "could not translate host name" (DNS error): Cursor's terminal often
cannot reach Supabase. Run the same command from the macOS Terminal app:
  open -a Terminal
  cd /Users/gianfrancoeliggi/Documents/cursor
  python3 sync_local_to_supabase.py

Requires: .streamlit/secrets.toml with DATABASE_URL pointing to Supabase.
"""
import os
import re

# Load DATABASE_URL from secrets so we connect to Supabase
secrets_path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
if os.path.exists(secrets_path):
    with open(secrets_path) as f:
        for line in f:
            m = re.match(r'DATABASE_URL\s*=\s*["\']([^"\']+)["\']', line.strip())
            if m:
                os.environ["DATABASE_URL"] = m.group(1)
                break

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use config after DATABASE_URL might be set
import config
from db.models import Base, Brand, Product, PriceHistory

SQLITE_PATH = config.DB_PATH
SUPABASE_URL = os.environ.get("DATABASE_URL") or getattr(config, "DATABASE_URL", None)


def _try_connect(url):
    """Try to connect; return (engine, None) on success or (None, error_message) on failure."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[11:]
    try:
        engine = create_engine(url, echo=False)
        with engine.connect() as conn:
            conn.close()
        return engine, None
    except Exception as e:
        return None, str(e)


def _build_pooler_url(main_url):
    """Build Supabase connection pooler URL (sometimes works when direct db.xxx.supabase.co fails)."""
    # main_url like postgresql://postgres:PASSWORD@db.REF.supabase.co:5432/postgres
    m = re.match(r"postgresql://([^:]+):([^@]+)@db\.([a-z0-9]+)\.supabase\.co:\d+/(.+)", main_url)
    if not m:
        return None
    user, password, ref, db = m.group(1), m.group(2), m.group(3), m.group(4)
    # Pooler format: postgresql://postgres.REF:PASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres
    return f"postgresql://postgres.{ref}:{password}@aws-0-us-east-1.pooler.supabase.com:6543/{db}"


def main():
    if not SUPABASE_URL:
        print("ERROR: DATABASE_URL not set. Add it to .streamlit/secrets.toml")
        return
    url = SUPABASE_URL.strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[11:]

    supabase_engine, err = _try_connect(url)
    if supabase_engine is None and "translate host name" in (err or ""):
        pooler_url = _build_pooler_url(url)
        if pooler_url:
            print("Direct Supabase host failed (DNS). Trying pooler URL...")
            supabase_engine, err = _try_connect(pooler_url)
    if supabase_engine is None:
        print("ERROR: Could not connect to Supabase.")
        print(err or "")
        print()
        print("Cursor's terminal often cannot reach Supabase (DNS). Run this script from the")
        print("macOS Terminal app instead:")
        print("  1. Open Terminal (Spotlight: Terminal)")
        print("  2. cd /Users/gianfrancoeliggi/Documents/cursor")
        print("  3. python3 sync_local_to_supabase.py")
        return

    sqlite_engine = create_engine(f"sqlite:///{SQLITE_PATH}", echo=False)

    # Create tables on Supabase if missing
    Base.metadata.create_all(supabase_engine)

    SessionLocal = sessionmaker(bind=sqlite_engine)
    SessionSupabase = sessionmaker(bind=supabase_engine)

    local = SessionLocal()
    remote = SessionSupabase()

    try:
        # 1. Brands: read from SQLite, insert into Supabase (skip if exists by name), build old_id -> new_id
        brands_local = local.query(Brand).order_by(Brand.id).all()
        brand_id_map = {}  # old_id -> new_id
        for b in brands_local:
            existing = remote.query(Brand).filter(Brand.name == b.name).first()
            if existing:
                brand_id_map[b.id] = existing.id
            else:
                new_b = Brand(name=b.name, base_url=b.base_url, active=b.active)
                remote.add(new_b)
                remote.flush()
                brand_id_map[b.id] = new_b.id
        remote.commit()
        print(f"Brands: {len(brand_id_map)} synced.")

        # 2. Products: read from SQLite, insert into Supabase (skip if same brand_id + url), build old_id -> new_id
        products_local = local.query(Product).order_by(Product.id).all()
        product_id_map = {}
        for p in products_local:
            new_brand_id = brand_id_map.get(p.brand_id)
            if new_brand_id is None:
                continue
            existing = remote.query(Product).filter(
                Product.brand_id == new_brand_id, Product.url == p.url
            ).first()
            if existing:
                product_id_map[p.id] = existing.id
            else:
                new_p = Product(
                    brand_id=new_brand_id,
                    name=p.name,
                    url=p.url,
                    category=p.category,
                    created_at=p.created_at,
                )
                remote.add(new_p)
                remote.flush()
                product_id_map[p.id] = new_p.id
        remote.commit()
        print(f"Products: {len(product_id_map)} synced.")

        # 3. Price history: insert into Supabase with mapped product_id (skip duplicates)
        history_local = local.query(PriceHistory).order_by(PriceHistory.id).all()
        inserted = 0
        skipped = 0
        for h in history_local:
            new_product_id = product_id_map.get(h.product_id)
            if new_product_id is None:
                continue
            exists = remote.query(PriceHistory).filter(
                PriceHistory.product_id == new_product_id,
                PriceHistory.scraped_at == h.scraped_at,
            ).first()
            if exists:
                skipped += 1
                continue
            new_h = PriceHistory(
                product_id=new_product_id,
                price=h.price,
                currency=h.currency,
                scraped_at=h.scraped_at,
            )
            remote.add(new_h)
            inserted += 1
        remote.commit()
        print(f"Price history: {inserted} new records synced, {skipped} already existed.")

        print("Done. Refresh your public app to see the data.")
    except Exception as e:
        remote.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        local.close()
        remote.close()


if __name__ == "__main__":
    main()
