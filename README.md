# Shapermint competitor price datascraper

This project scrapes shapewear prices from Shapermint's main competitors (Spanx, SKIMS, Honeylove), stores them in a local SQLite database with full history, and provides a **Streamlit dashboard** for the team to view current prices, filter by brand/category, and see price trends over time.

## Setup

1. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   python -m playwright install chromium
   ```

   (Playwright + Chromium are required for SKIMS and Honeylove; Spanx uses requests.)

2. **Run the dashboard**

   ```bash
   streamlit run app.py
   ```

   The app opens in your browser. Use the sidebar and tabs to:
   - **Current prices**: View latest prices; filter by brand or category.
   - **Price history**: Select products and see a line chart of price over time.
   - **Run scrape**: Click "Execute scrape" to fetch fresh data from competitor sites (first run may take a few minutes; SKIMS and Honeylove use a headless browser).

## Data storage

- **Local (default):** Prices are stored in a SQLite database at `data/prices.db`. The `data/` folder is gitignored.
- **Cloud (optional):** Set `DATABASE_URL` (e.g. PostgreSQL on Supabase, Neon) so the app uses that DB instead of SQLite. Data then persists when you deploy the app.

## Optional: scheduled scraping

To refresh prices on a schedule (e.g. daily) without using the UI:

1. Use a cron job or task scheduler to run:

   ```bash
   python -c "from scrapers import run_all_scrapers; run_all_scrapers(save=True)"
   ```

   Run this from the project root so that `config` and `db` resolve correctly.

2. Or use a tool like `schedule` or APScheduler inside a small script; the same call `run_all_scrapers(save=True)` is the entry point.

## Project structure

- `app.py` – Streamlit UI entry point.
- `config.py` – DB path, scrape delays, brand keys, collection URLs.
- `db/` – SQLAlchemy models, DB init, read/write helpers.
- `scrapers/` – Per-brand scrapers (Spanx, SKIMS, Honeylove) and orchestrator in `base.py`.
- `data/` – SQLite file (created at runtime; not committed).

## Deploy and share (only you can update data)

1. **Push the repo to GitHub** (public or private).

2. **Deploy on [Streamlit Community Cloud](https://share.streamlit.io):**
   - Sign in with GitHub, connect the repo, set **Main file path** to `app.py`.
   - In **Settings → Secrets**, add:
     - `SCRAPE_PASSWORD` = a password only you know (so only you can run "Execute scrape").
     - `DATABASE_URL` = your cloud PostgreSQL URL (e.g. from [Supabase](https://supabase.com) or [Neon](https://neon.tech)) so data persists between deploys.
   - Deploy. Share the app URL with your team.

3. **Who sees what:**
   - Everyone can open the app and see **Current prices** and **Price history**.
   - Only someone who enters the correct password in the sidebar can see and use **Run scrape** (Execute scrape).

4. **Updating data when deployed:**
   - **Option A:** Run the app locally with the same `DATABASE_URL` (e.g. in `.streamlit/secrets.toml` or env), log in with the password, and click "Execute scrape". Data is written to the cloud DB; the deployed app shows it.
   - **Option B:** On Streamlit Cloud, scrapes that need Playwright (SKIMS, Honeylove) may not run; only Spanx (requests) might work. For full scrapes, run locally with `DATABASE_URL` set to your cloud DB.

5. **Local secrets (optional):** Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and set `SCRAPE_PASSWORD` and/or `DATABASE_URL`. Do not commit `secrets.toml`.

## Notes

- **Spanx** is scraped with `requests` + BeautifulSoup. **SKIMS** and **Honeylove** use Playwright (headless Chromium) because their product grids are JS-rendered.
- Product names are cleaned (encoding fixes, removal of "Quick shop", "Best Seller", etc.).
- Respect each site’s `robots.txt` and use the app for internal team use only.
