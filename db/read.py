"""Read queries for the Streamlit UI."""
from db.models import Product, PriceHistory, Brand, get_session, init_db


def get_current_prices(brand_name=None, category=None):
    """
    Return a list of dicts with: brand_name, product_name, category, price, currency, scraped_at, product_id, url.
    Optional filters: brand_name, category.
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
        if brand_name:
            q = q.filter(Brand.name == brand_name)
        if category:
            q = q.filter(Product.category == category)
        products = q.all()
        result = []
        for row in products:
            latest = (
                session.query(PriceHistory)
                .filter(PriceHistory.product_id == row.product_id)
                .order_by(PriceHistory.scraped_at.desc())
                .first()
            )
            if latest:
                result.append({
                    "brand_name": row.brand_name,
                    "product_name": row.product_name,
                    "category": row.category or "",
                    "price": float(latest.price),
                    "currency": latest.currency,
                    "scraped_at": latest.scraped_at,
                    "product_id": row.product_id,
                    "url": row.url,
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
