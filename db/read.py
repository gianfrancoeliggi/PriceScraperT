"""Read queries for the Streamlit UI."""
from sqlalchemy import func

from db.models import Product, PriceHistory, Brand, get_session, init_db


def get_last_scrape_at():
    """Return the most recent scraped_at timestamp across all price_history, or None."""
    init_db()
    session = get_session()
    try:
        row = session.query(func.max(PriceHistory.scraped_at)).scalar()
        return row
    finally:
        session.close()


def get_current_prices(brand_names=None, category_names=None):
    """
    Return a list of dicts with: brand_name, product_name, category, price, currency,
    scraped_at, product_id, url, previous_price, change_pct.
    Optional filters: brand_names (list), category_names (list). None = no filter.
    """
    init_db()
    session = get_session()
    try:
        q = (
            session.query(
                Brand.name.label("brand_name"),
                Product.name.label("product_name"),
                Product.category.label("category"),
                Product.id.label("product_id"),
                Product.url.label("url"),
            )
            .join(Product, Product.brand_id == Brand.id)
            .filter(Brand.active == True)
        )
        if brand_names:
            q = q.filter(Brand.name.in_(brand_names))
        if category_names:
            q = q.filter(Product.category.in_(category_names))
        products = q.all()
        result = []
        for row in products:
            histories = (
                session.query(PriceHistory)
                .filter(PriceHistory.product_id == row.product_id)
                .order_by(PriceHistory.scraped_at.desc())
                .limit(2)
                .all()
            )
            if not histories:
                continue
            latest = histories[0]
            previous_price = float(histories[1].price) if len(histories) > 1 else None
            change_pct = None
            if previous_price is not None and previous_price != 0:
                change_pct = round(
                    (float(latest.price) - previous_price) / previous_price * 100, 1
                )
            result.append({
                "brand_name": row.brand_name,
                "product_name": row.product_name,
                "category": row.category or "",
                "price": float(latest.price),
                "currency": latest.currency,
                "scraped_at": latest.scraped_at,
                "product_id": row.product_id,
                "url": row.url,
                "previous_price": previous_price,
                "change_pct": change_pct,
            })
        return result
    finally:
        session.close()


def get_products_for_selector():
    """Return list of (product_id, display_name) for dropdowns. display_name = brand - product name."""
    init_db()
    session = get_session()
    try:
        rows = (
            session.query(Product.id, Brand.name, Product.name)
            .join(Brand, Product.brand_id == Brand.id)
            .order_by(Brand.name, Product.name)
            .all()
        )
        return [(r[0], f"{r[1]} – {r[2]}") for r in rows]
    finally:
        session.close()


def get_price_history(product_ids):
    """
    Return list of dicts: product_id, product_display_name, scraped_at, price, currency.
    product_ids can be a single int or list of ints.
    """
    if isinstance(product_ids, int):
        product_ids = [product_ids]
    if not product_ids:
        return []
    init_db()
    session = get_session()
    try:
        rows = (
            session.query(
                PriceHistory.product_id,
                Brand.name,
                Product.name,
                PriceHistory.scraped_at,
                PriceHistory.price,
                PriceHistory.currency,
            )
            .join(Product, Product.id == PriceHistory.product_id)
            .join(Brand, Brand.id == Product.brand_id)
            .filter(PriceHistory.product_id.in_(product_ids))
            .order_by(PriceHistory.product_id, PriceHistory.scraped_at)
            .all()
        )
        return [
            {
                "product_id": r.product_id,
                "product_display_name": f"{r[1]} – {r[2]}",
                "scraped_at": r.scraped_at,
                "price": float(r.price),
                "currency": r.currency,
            }
            for r in rows
        ]
    finally:
        session.close()


def get_brand_names():
    """Return sorted list of brand names that have products."""
    init_db()
    session = get_session()
    try:
        rows = session.query(Brand.name).filter(Brand.active == True).distinct().all()
        return sorted(r[0] for r in rows)
    finally:
        session.close()


def get_categories():
    """Return sorted list of distinct categories (non-empty)."""
    init_db()
    session = get_session()
    try:
        rows = (
            session.query(Product.category)
            .filter(Product.category != None, Product.category != "")
            .distinct()
            .all()
        )
        return sorted(r[0] for r in rows)
    finally:
        session.close()
