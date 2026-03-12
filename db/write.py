"""Persistence logic: save scraper results to the database."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from db.models import Brand, Product, PriceHistory, get_session, init_db
from db.read import AMAZON_DISPLAY_PRICE_MIN, AMAZON_DISPLAY_PRICE_MAX


def _get_or_create_brand(session: Session, name: str, base_url: Optional[str] = None) -> Brand:
    brand = session.query(Brand).filter(Brand.name == name).first()
    if brand is None:
        brand = Brand(name=name, base_url=base_url)
        session.add(brand)
        session.flush()
    return brand


def _get_or_create_product(
    session: Session,
    brand_id: int,
    name: str,
    url: str,
    category: Optional[str] = None,
) -> Product:
    product = (
        session.query(Product)
        .filter(Product.brand_id == brand_id, Product.url == url)
        .first()
    )
    if product is None:
        product = Product(brand_id=brand_id, name=name, url=url, category=category)
        session.add(product)
        session.flush()
    else:
        if category and product.category != category:
            product.category = category
    return product


def save_scrape_results(items: list[dict]) -> tuple[int, int]:
    """
    Persist a list of scraped items to the database.
    Each item must have: name, brand, category (optional), price, currency (optional), url.
    Returns (products_updated, price_records_inserted).
    """
    init_db()
    session = get_session()
    try:
        products_updated = 0
        price_records_inserted = 0
        now = datetime.utcnow()
        for item in items:
            brand_name = item.get("brand") or "Unknown"
            base_url = item.get("base_url")
            brand = _get_or_create_brand(session, brand_name, base_url)
            product = _get_or_create_product(
                session,
                brand_id=brand.id,
                name=item["name"],
                url=item["url"],
                category=item.get("category"),
            )
            products_updated += 1
            price = item.get("price")
            if price is not None:
                if isinstance(price, (int, float)):
                    price = Decimal(str(price))
                session.add(
                    PriceHistory(
                        product_id=product.id,
                        price=price,
                        currency=item.get("currency") or "USD",
                        scraped_at=now,
                    )
                )
                price_records_inserted += 1
        session.commit()
        return products_updated, price_records_inserted
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def delete_bogus_amazon_price_history() -> int:
    """
    Delete PriceHistory rows for Shapermint Amazon where price is outside 5–500 USD.
    Returns number of rows deleted. Run once to clean old bogus data.
    """
    init_db()
    session = get_session()
    try:
        brand = session.query(Brand).filter(Brand.name == "Shapermint Amazon").first()
        if not brand:
            return 0
        subq = session.query(Product.id).filter(Product.brand_id == brand.id)
        to_delete = (
            session.query(PriceHistory)
            .filter(
                PriceHistory.product_id.in_(subq),
                or_(
                    PriceHistory.price < AMAZON_DISPLAY_PRICE_MIN,
                    PriceHistory.price > AMAZON_DISPLAY_PRICE_MAX,
                ),
            )
            .all()
        )
        n = len(to_delete)
        for row in to_delete:
            session.delete(row)
        session.commit()
        return n
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
