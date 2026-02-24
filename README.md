# Shapermint competitor price scraper

Scrapes shapewear prices from Spanx, SKIMS, and Honeylove, stores them in Supabase, and shows them in a shared Streamlit dashboard (current prices, filters, price history charts).

---

## Architecture

```
Your Mac
  └── run_scrape_once.py
        ├── Spanx  → requests + BeautifulSoup
        ├── SKIMS  → Playwright (headless Chromium)
        └── Honeylove → Playwright (headless Chromium)
              │
              ▼
         Supabase (PostgreSQL, cloud)
              │
              ▼
     Streamlit Cloud (public app)
       anyone with the URL can view prices & history
```

- The scraper runs **locally on your Mac** and writes **directly to Supabase**.
- The public app on Streamlit Cloud reads from the same Supabase database.
- Data appears in the public app immediately after you run a scrape — no reboot needed.

---

## Daily workflow (updating data)

Open a terminal in the project folder and run:

```bash
python3 run_scrape_once.py
```

That's it. All 3 brands are scraped and results go straight to Supabase.

---

## Setup (first time on a new machine)

1. **Install dependencies:**

   ```bash
   pip3 install -r requirements.txt
   python3 -m playwright install chromium
   ```

2. **Create `.streamlit/secrets.toml`** with:

   ```toml
   SCRAPE_PASSWORD = 'my-admin-password'
   DATABASE_URL = 'postgresql://postgres.yiybgogqeehgrrbhrgti:PASSWORD@aws-1-us-east-1.pooler.supabase.com:5432/postgres'
   ```

   Use the **Session Pooler** URL from Supabase (Settings → Database → Connect → Session pooler). The direct connection URL does NOT work on IPv4 networks.

3. **Run locally:**

   ```bash
   python3 -m streamlit run app.py
   ```

---

## Project structure

- `app.py` — Streamlit UI (current prices, price history, run scrape tab).
- `config.py` — DB path, scrape delays, brand keys, collection URLs.
- `db/` — SQLAlchemy models, read/write helpers.
- `scrapers/` — Per-brand scrapers and orchestrator (`base.py`).
- `run_scrape_once.py` — Run all scrapers from the terminal (no UI needed).
- `sync_local_to_supabase.py` — Fallback: syncs local SQLite to Supabase (only needed if you scraped offline without internet).
- `data/` — Local SQLite fallback (created at runtime if Supabase unreachable; not committed).

---

## Deployment

- **App code** lives on GitHub (`gianfrancoeliggi/PriceScraperT`) and is deployed via Streamlit Cloud.
- **Data** lives in Supabase — completely separate from the code.
- Push to GitHub only when you change code (app.py, scrapers, etc.). Data updates never require a GitHub push or app reboot.

### Streamlit Cloud secrets

In share.streamlit.io → your app → Settings → Secrets:

```toml
SCRAPE_PASSWORD = 'my-admin-password'
DATABASE_URL = 'postgresql://postgres.yiybgogqeehgrrbhrgti:PASSWORD@aws-1-us-east-1.pooler.supabase.com:5432/postgres'
```

---

## Supabase connection notes

- The **direct connection** (`db.xxx.supabase.co`) is IPv6-only — does not work on standard home/office networks.
- Always use the **Session Pooler** URL (`aws-1-us-east-1.pooler.supabase.com`, port 5432) which works on IPv4.
- The pooler username format is `postgres.PROJECTREF` (not just `postgres`).

---

## Notes

- **Spanx** uses `requests` + BeautifulSoup. **SKIMS** and **Honeylove** use Playwright (headless Chromium) because their pages are JS-rendered.
- Playwright + Chromium must be installed locally to scrape SKIMS and Honeylove.
- On Streamlit Cloud, only Spanx can be scraped via the "Run scrape" tab (no Playwright). Always scrape locally.
- Respect each site's `robots.txt`. This tool is for internal team use only.
