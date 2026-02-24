"""Database package: models and persistence for price scraper."""
from db.models import (
    Base,
    Brand,
    Product,
    PriceHistory,
    get_engine,
    get_session,
    init_db,
    is_using_sqlite_fallback,
)

__all__ = [
    "Base",
    "Brand",
    "Product",
    "PriceHistory",
    "get_engine",
    "get_session",
    "init_db",
    "is_using_sqlite_fallback",
]
