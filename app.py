"""
Shapermint competitor price datascraper – Streamlit UI.
Run with: streamlit run app.py
"""
import os
import streamlit as st

# So config and db use cloud DB when deployed (Streamlit Secrets → os.environ)
try:
    for key in ("DATABASE_URL", "SCRAPE_PASSWORD", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "USE_VISION_PRICES"):
        v = getattr(st.secrets, key, None) or (st.secrets.get(key) if hasattr(st.secrets, "get") else None)
        if v:
            os.environ[key] = str(v)
except Exception:
    pass

from db import init_db, is_using_sqlite_fallback
from db.read import (
    get_current_prices,
    get_last_scrape_at,
    get_price_history,
    get_products_for_selector,
    get_brand_names,
    get_categories,
    get_shapermint_comparison,
    get_shapermint_price_history_for_category,
)
from db.write import delete_bogus_amazon_price_history
from scrapers import run_all_scrapers

st.set_page_config(
    page_title="Shapermint Competitor Prices",
    page_icon="📊",
    layout="wide",
)

# Connect to DB: use Supabase if reachable, otherwise fall back to local SQLite (e.g. when run from Cursor with no network).
init_db()

# Admin access: only users who know the password can run scrapes (when SCRAPE_PASSWORD is set)
def _get_scrape_password():
    try:
        return st.secrets.get("SCRAPE_PASSWORD") or st.secrets.get("scrape_password")
    except Exception:
        return None

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

with st.sidebar:
    st.markdown("## About")
    if is_using_sqlite_fallback():
        st.warning("Local DB (Supabase unavailable). Data here won’t appear in the public app.")
        st.caption("Run `python3 sync_local_to_supabase.py` from the project folder to sync.")
    st.caption(
        "**Current prices** shows competitors only (Spanx, SKIMS, Honeylove). "
        "Use the **Shapermint: Amazon vs Store** tab to compare Shapermint Amazon vs Shapermint Store by category."
    )
    st.markdown("---")
    scrape_password = _get_scrape_password()
    with st.expander("Admin", expanded=False):
        if scrape_password:
            if st.session_state.is_admin:
                st.success("Logged in.")
                if st.button("Log out"):
                    st.session_state.is_admin = False
                    st.rerun()
            else:
                pwd = st.text_input("Password", type="password", key="admin_pwd")
                if st.button("Log in"):
                    if pwd == scrape_password:
                        st.session_state.is_admin = True
                        st.rerun()
                    else:
                        st.error("Wrong password.")
            if st.session_state.is_admin:
                st.markdown("---")
                st.caption("Run a scrape to refresh prices.")
                if st.button("Execute scrape"):
                    with st.spinner("Scraping…"):
                        try:
                            result = run_all_scrapers(save=True)
                            items = result["items"]
                            products_updated = result["products_updated"]
                            price_records = result["price_records_inserted"]
                            per_brand = result["per_brand"]
                            st.success(
                                f"Done. **{len(items)}** items, **{products_updated}** products, **{price_records}** price records."
                            )
                            for brand, (count, err) in per_brand.items():
                                if err:
                                    st.warning(f"**{brand}:** {err}")
                                else:
                                    st.caption(f"**{brand}:** {count} items")
                            if result.get("cloud_only_spanx"):
                                st.info(
                                    "Cloud run — only Spanx scraped. "
                                    "Run the app locally for SKIMS, Honeylove, Shapermint (Amazon), and Shapermint Store."
                                )
                        except Exception as e:
                            st.error(f"Scrape failed: {e}")
                st.caption("Remove old bogus Amazon price records (e.g. $56,615) from the database.")
                if st.button("Clean bogus Amazon prices"):
                    try:
                        n = delete_bogus_amazon_price_history()
                        st.success(f"Deleted **{n}** bogus Amazon price record(s). Refresh the comparison tab.")
                    except Exception as e:
                        st.error(f"Cleanup failed: {e}")
        else:
            st.caption("Set **SCRAPE_PASSWORD** in secrets to enable updates.")

# Tabs for main sections
tab1, tab2, tab3 = st.tabs([
    "📊 Current prices",
    "🔄 Shapermint: Amazon vs Store",
    "📈 Price history",
])

import pandas as pd

with tab1:
    st.header("Current prices")
    st.caption("Latest scraped price per product. Use filters to narrow down.")
    brands = get_brand_names()
    categories = get_categories()

    col1, col2 = st.columns(2)
    with col1:
        filter_brands = st.multiselect(
            "Brands",
            options=brands,
            default=[],
            key="ms_brands",
        )
    with col2:
        filter_categories = st.multiselect(
            "Categories",
            options=categories,
            default=[],
            key="ms_categories",
        )
    search_query = st.text_input(
        "Search by product name",
        placeholder="Type to filter…",
        key="search_input",
    )

    # Filter pills and Clear all
    active_filters = []
    if filter_brands:
        active_filters.append("Brands: " + ", ".join(filter_brands))
    if filter_categories:
        active_filters.append("Categories: " + ", ".join(filter_categories))
    if search_query and search_query.strip():
        active_filters.append("Search: '" + search_query.strip() + "'")
    if active_filters:
        pill_col, clear_col = st.columns([3, 1])
        with pill_col:
            st.caption("Active: " + "  |  ".join(active_filters))
        with clear_col:
            if st.button("Clear all"):
                st.session_state.ms_brands = []
                st.session_state.ms_categories = []
                st.session_state.search_input = ""
                st.rerun()

    competitor_brands = [b for b in brands if b not in ("Shapermint Amazon", "Shapermint Store")]
    brand_names = filter_brands if filter_brands else competitor_brands
    category_names = filter_categories if filter_categories else None
    rows = get_current_prices(brand_names=brand_names, category_names=category_names)

    if search_query and search_query.strip():
        q = search_query.strip().lower()
        rows = [r for r in rows if q in (r.get("product_name") or "").lower()]

    if not rows:
        st.info("No price data yet. Use **Admin** in the sidebar to run a scrape.")
    else:
        df = pd.DataFrame(rows)

        # Global last scrape
        last_scrape = get_last_scrape_at()
        if last_scrape:
            try:
                ts = pd.Timestamp(last_scrape).strftime("%b %d, %H:%M")
            except Exception:
                ts = str(last_scrape)
            st.caption(f"Last scrape: **{ts}**")

        # KPI strip
        min_price = df["price"].min()
        max_price = df["price"].max()
        count = len(df)
        avg_by_brand = df.groupby("brand_name")["price"].mean().round(2)
        kpi_parts = [f"**{b}** ${v:,.2f}" for b, v in avg_by_brand.items()]
        kpi_str = " | ".join(kpi_parts) if kpi_parts else "—"
        st.markdown(
            f"Avg by brand: {kpi_str}  ·  "
            f"Min **${min_price:,.2f}**  ·  Max **${max_price:,.2f}**  ·  "
            f"**{count}** products"
        )

        # Sort dropdown
        sort_col, sort_dir = st.columns(2)
        with sort_col:
            sort_by = st.selectbox(
                "Sort by",
                options=["price", "brand_name", "category", "scraped_at"],
                format_func=lambda x: {"price": "Price", "brand_name": "Brand", "category": "Category", "scraped_at": "Last updated"}[x],
                key="sort_by",
            )
        with sort_dir:
            sort_asc = st.selectbox("Order", options=[True, False], format_func=lambda x: "Ascending" if x else "Descending", key="sort_asc")
        df = df.sort_values(by=sort_by, ascending=sort_asc).reset_index(drop=True)

        # Truncate product name for display; keep full for tooltip
        max_name_len = 40
        df["product_display"] = df["product_name"].apply(
            lambda x: (x[:max_name_len] + "...") if x and len(str(x)) > max_name_len else (x or "")
        )

        # Format price with commas; build display df
        df["price_fmt"] = df["price"].apply(lambda p: f"{p:,.2f}")
        df["previous_fmt"] = df["previous_price"].apply(
            lambda p: f"{p:,.2f}" if p is not None else "—"
        )
        df["change_fmt"] = df["change_pct"].apply(
            lambda c: f"{c:+.1f}%" if c is not None else "—"
        )

        # Min/max in view for highlighting
        view_min, view_max = df["price"].min(), df["price"].max()

        display_df = df[["brand_name", "product_display", "category", "price_fmt", "previous_fmt", "change_fmt", "currency"]].copy()
        display_df = display_df.rename(columns={
            "brand_name": "Brand",
            "product_display": "Product",
            "category": "Category",
            "price_fmt": "Price",
            "previous_fmt": "Previous price",
            "change_fmt": "Change %",
            "currency": "Currency",
        })

        def row_style(r):
            p = df.loc[r.name, "price"]
            if p == view_min:
                return ["", "", "", "background-color: #d4edda;", "", "", ""]
            if p == view_max:
                return ["", "", "", "background-color: #f8d7da;", "", "", ""]
            return [""] * 7

        styled = display_df.style.apply(row_style, axis=1)

        column_config = {
            "Brand": st.column_config.TextColumn("Brand", width="small"),
            "Product": st.column_config.TextColumn(
                "Product",
                width="medium",
                help="Truncated; full name in exported CSV",
            ),
            "Category": st.column_config.TextColumn("Category", width="small"),
            "Price": st.column_config.TextColumn("Price", width="small"),
            "Previous price": st.column_config.TextColumn("Previous price", width="small"),
            "Change %": st.column_config.TextColumn("Change %", width="small"),
            "Currency": st.column_config.TextColumn("Currency", width="small"),
        }
        st.dataframe(
            styled,
            use_container_width=True,
            hide_index=True,
            column_config=column_config,
            height=400,
        )
        # Export CSV
        csv_bytes = df[["brand_name", "product_name", "category", "price", "previous_price", "change_pct", "currency"]].to_csv(index=False).encode()
        st.download_button("Export CSV", data=csv_bytes, file_name="current_prices.csv", mime="text/csv", key="export_csv")

# Category order for Amazon vs Store comparison
SHAPERMINT_CATEGORY_ORDER = [
    "EBRA", "STBRA", "CAMI", "Sweetheart BRA", "Tank CAMI", "BRAHE", "BSS",
]
# Ignore bogus Amazon prices (old scrape bugs / wrong locale); same range as scraper
_AMAZON_PRICE_MIN, _AMAZON_PRICE_MAX = 5.0, 500.0

with tab2:
    st.header("Shapermint: Amazon vs Store")
    st.caption("Compare Shapermint Amazon and Shapermint Store prices by category.")
    comparison = get_shapermint_comparison()
    if not comparison:
        st.info(
            "No Shapermint Amazon or Store data yet. "
            "**Shapermint** and **shapermint_store** use Playwright and don't run on Streamlit Cloud. "
            "Run the app locally (`streamlit run app.py`), open **Admin** → **Execute scrape**, then run the scrape. "
            "Data is saved to the same database, so it will appear here and on the deployed app."
        )
    else:
        df_comp = pd.DataFrame(comparison)
        # Build a summary by category: Amazon (min–max or list), Store 1 unit, Store 2 pack
        amazon_by_cat = {}
        store_1_by_cat = {}
        store_2_by_cat = {}
        for _, row in df_comp.iterrows():
            cat = row.get("category") or ""
            brand = row.get("brand_name") or ""
            price = row.get("price")
            name = row.get("product_name") or ""
            if "Amazon" in brand:
                if cat not in amazon_by_cat:
                    amazon_by_cat[cat] = []
                if price is not None and _AMAZON_PRICE_MIN <= float(price) <= _AMAZON_PRICE_MAX:
                    amazon_by_cat[cat].append(float(price))
            elif "Store" in brand:
                if "2 Pack" in name or "2 pack" in name:
                    store_2_by_cat[cat] = price
                else:
                    store_1_by_cat[cat] = price
        rows_comp = []
        for cat in SHAPERMINT_CATEGORY_ORDER:
            if cat not in amazon_by_cat and cat not in store_1_by_cat and cat not in store_2_by_cat:
                continue
            am_prices = amazon_by_cat.get(cat) or []
            am_str = f"${min(am_prices):,.2f} – ${max(am_prices):,.2f}" if am_prices else "—"
            if len(am_prices) == 1:
                am_str = f"${am_prices[0]:,.2f}"
            rows_comp.append({
                "Category": cat,
                "Amazon": am_str,
                "Store 1 unit": f"${store_1_by_cat[cat]:,.2f}" if store_1_by_cat.get(cat) is not None else "—",
                "Store 2 pack": f"${store_2_by_cat[cat]:,.2f}" if store_2_by_cat.get(cat) is not None else "—",
            })
        if rows_comp:
            st.dataframe(
                pd.DataFrame(rows_comp),
                use_container_width=True,
                hide_index=True,
            )
        st.subheader("All products")
        # Hide Amazon rows with bogus price so table matches summary
        def _valid_price(row):
            p = row.get("price")
            if p is None:
                return False
            if "Amazon" in (row.get("brand_name") or ""):
                return _AMAZON_PRICE_MIN <= float(p) <= _AMAZON_PRICE_MAX
            return True
        display_comp = df_comp[["brand_name", "product_name", "category", "price", "currency", "scraped_at"]].copy()
        display_comp = display_comp[display_comp.apply(_valid_price, axis=1)]
        display_comp["scraped_at"] = pd.to_datetime(display_comp["scraped_at"], errors="coerce")
        display_comp = display_comp.rename(columns={
            "brand_name": "Brand",
            "product_name": "Product",
            "category": "Category",
            "price": "Price",
            "currency": "Currency",
            "scraped_at": "Scraped at",
        })
        display_comp["Price"] = display_comp["Price"].apply(lambda p: f"{p:,.2f}")
        cols_display = ["Brand", "Product", "Category", "Price", "Currency", "Scraped at"]
        st.dataframe(
            display_comp[cols_display],
            use_container_width=True,
            hide_index=True,
            column_config={"Scraped at": st.column_config.DatetimeColumn("Scraped at", format="YYYY-MM-DD HH:mm")},
        )

with tab3:
    st.header("Price history")
    st.caption("Select one or more products to see how their price changed over time.")
    product_options = get_products_for_selector()
    if not product_options:
        st.info("No products in the database yet. Use **Admin** in the sidebar to run a scrape.")
    else:
        selected = st.multiselect(
            "Choose products",
            options=[pid for pid, _ in product_options],
            format_func=lambda pid: next((label for id_, label in product_options if id_ == pid), str(pid)),
        )
        if selected:
            history = get_price_history(selected)
            if not history:
                st.warning("No price history for the selected product(s).")
            else:
                import pandas as pd
                df = pd.DataFrame(history)
                df["scraped_at"] = pd.to_datetime(df["scraped_at"])
                # Pivot for line chart: one column per product
                pivot = df.pivot_table(
                    index="scraped_at", columns="product_display_name", values="price"
                ).ffill()
                if not pivot.empty:
                    st.line_chart(pivot, use_container_width=True)
                st.dataframe(
                    df[["product_display_name", "scraped_at", "price", "currency"]].rename(
                        columns={
                            "product_display_name": "Product",
                            "scraped_at": "Date",
                            "price": "Price",
                            "currency": "Currency",
                        }
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
        else:
            st.info("Select at least one product to view history.")

    st.subheader("Shapermint: Amazon vs Store over time")
    st.caption("Pick a category to see price history for Amazon vs Store (1 unit and 2 pack).")
    shapermint_cats = [c for c in SHAPERMINT_CATEGORY_ORDER if c in (get_categories() or [])]
    if not shapermint_cats:
        st.info("No Shapermint Amazon or Store data yet. Run those scrapers first.")
    else:
        comp_cat = st.selectbox(
            "Category",
            options=shapermint_cats,
            key="shapermint_history_cat",
        )
        if comp_cat:
            hist_rows = get_shapermint_price_history_for_category(comp_cat)
            if not hist_rows:
                st.warning(f"No price history for category **{comp_cat}**.")
            else:
                df_h = pd.DataFrame(hist_rows)
                df_h["scraped_at"] = pd.to_datetime(df_h["scraped_at"])
                # Filter bogus Amazon prices for the chart
                def _ok(row):
                    if "Amazon" in (row.get("brand_name") or ""):
                        p = row.get("price")
                        return p is not None and _AMAZON_PRICE_MIN <= float(p) <= _AMAZON_PRICE_MAX
                    return True
                df_h = df_h[df_h.apply(_ok, axis=1)]
                # Build series: Amazon (min per scraped_at), Store 1 unit, Store 2 pack
                by_ts = df_h.groupby("scraped_at")
                chart_data = []
                for ts, grp in by_ts:
                    row = {"scraped_at": ts}
                    am = grp[grp["brand_name"] == "Shapermint Amazon"]
                    if not am.empty:
                        row["Amazon"] = am["price"].min()
                    store = grp[grp["brand_name"] == "Shapermint Store"]
                    store_1 = store[~store["product_name"].str.contains("2 [Pp]ack", na=False)]
                    store_2 = store[store["product_name"].str.contains("2 [Pp]ack", na=False)]
                    if not store_1.empty:
                        row["Store 1 unit"] = store_1["price"].iloc[0]
                    if not store_2.empty:
                        row["Store 2 pack"] = store_2["price"].iloc[0]
                    chart_data.append(row)
                if chart_data:
                    df_chart = pd.DataFrame(chart_data).set_index("scraped_at").sort_index()
                    df_chart = df_chart.ffill()
                    st.line_chart(df_chart, use_container_width=True)
                    st.dataframe(df_chart.reset_index(), use_container_width=True, hide_index=True)
                else:
                    st.warning("No data to plot after filtering.")
