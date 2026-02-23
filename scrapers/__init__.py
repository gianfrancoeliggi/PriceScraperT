"""Scrapers for competitor shapewear prices."""
from scrapers.base import scrape_brand, run_all_scrapers

# Import scrapers so they register with base
from scrapers import spanx  # noqa: F401
from scrapers import skims  # noqa: F401
from scrapers import honeylove  # noqa: F401

__all__ = ["scrape_brand", "run_all_scrapers"]
