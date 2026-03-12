"""Configuration for the Shapermint competitor price datascraper."""
import os

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "prices.db")

# Optional: cloud database (PostgreSQL). When set, app uses this instead of SQLite.
# Example: postgresql://user:pass@host:5432/dbname (Streamlit Cloud: set in Secrets)
DATABASE_URL = os.environ.get("DATABASE_URL")

# Scraping
REQUEST_DELAY_SECONDS = 1.5
# Use screenshot + AI vision to extract prices (avoids "Save $17" etc). Requires OPENAI_API_KEY.
USE_VISION_PRICES = os.environ.get("USE_VISION_PRICES", "").strip().lower() in ("1", "true", "yes")
USER_AGENT = (
    "ShapermintPriceScraper/1.0 (+https://github.com/shapermint; internal use)"
)

# Brand keys (used by orchestrator)
BRAND_KEYS = ["spanx", "skims", "honeylove", "shapermint", "shapermint_store"]

# Optional: collection URLs per brand (can be overridden in each scraper module)
SPANX_COLLECTIONS = [
    "https://www.spanx.com/collections/spanxshape",
    "https://www.spanx.com/collections/spanxsupersmooth-shapewear",
    "https://www.spanx.com/collections/spanxsculpt",
    "https://www.spanx.com/collections/leggings",
    "https://www.spanx.com/collections/best-sellers",
    "https://www.spanx.com/collections/spanxsupersculpt",
]
SKIMS_SHAPEWEAR_URL = "https://skims.com/collections/shapewear"
HONEYLOVE_SHAPEWEAR_URL = "https://www.honeylove.com/collections/shapewear"
