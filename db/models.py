"""SQLAlchemy models and DB initialization for price history."""
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

import config

Base = declarative_base()


class Brand(Base):
    __tablename__ = "brands"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False, unique=True)
    base_url = Column(String(512), nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    products = relationship("Product", back_populates="brand")


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, autoincrement=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    name = Column(String(512), nullable=False)
    url = Column(String(1024), nullable=False)
    category = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    brand = relationship("Brand", back_populates="products")
    price_history = relationship("PriceHistory", back_populates="product", order_by="PriceHistory.scraped_at")


class PriceHistory(Base):
    __tablename__ = "price_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(8), default="USD", nullable=False)
    scraped_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    product = relationship("Product", back_populates="price_history")


_engine = None
_Session = None


def get_engine():
    global _engine
    if _engine is None:
        if getattr(config, "DATABASE_URL", None):
            url = config.DATABASE_URL
            # SQLAlchemy expects postgresql:// (not postgres://)
            if url.startswith("postgres://"):
                url = "postgresql://" + url[11:]
            _engine = create_engine(url, echo=False)
        else:
            os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
            _engine = create_engine(f"sqlite:///{config.DB_PATH}", echo=False)
    return _engine


def get_session():
    global _Session
    if _Session is None:
        _Session = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _Session()


def init_db():
    """Create all tables if they do not exist."""
    engine = get_engine()
    Base.metadata.create_all(engine)
