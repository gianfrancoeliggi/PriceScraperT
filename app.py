"""
Shapermint competitor price datascraper – Streamlit UI.
Run with: streamlit run app.py
"""
import streamlit as st

from db import init_db
from db.read import (
    get_current_prices,
    get_price_history,
    get_products_for_selector,
    get_brand_names,
    get_categories,
)
from scrapers import run_all_scrapers

st.set_page_config(
    page_title="Shapermint Competitor Prices",
    page_icon="📊",
    layout="wide",
)

# Admin access: only users who know the password can run scrapes (when SCRAPE_PASSWORD is set)
def _get_scrape_password():
    try:
        return st.secrets.get("SCRAPE_PASSWORD") or st.secrets.get("scrape_password")
    except Exception:
        return None

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

with st.sidebar:
    st.markdown("## About this tool")
    st.markdown(
        "This dashboard shows **shapewear prices** from Shapermint's main competitors "
        "(Spanx, SKIMS, Honeylove). Use the tabs to view current prices, "
        "filter by brand or category, and see price history over time."
    )
    scrape_password = _get_scrape_password()
    if scrape_password:
        st.markdown("---")
        st.markdown("### Admin (update data)")
        if st.session_state.is_admin:
            st.success("Logged in as admin.")
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
    else:
        st.markdown("---")
        st.caption("(No admin password set — Run scrape is available to everyone.)")
    st.markdown("---")

init_db()

# Tabs for main sections
tab1, tab2, tab3 = st.tabs(["Current prices", "Price history", "Run scrape"])

with tab1:
    st.header("Current prices")
    st.caption("Latest scraped price per product. Use filters to narrow down.")
    brands = get_brand_names()
    categories = get_categories()
    col1, col2 = st.columns(2)
    with col1:
        filter_brand = st.selectbox(
            "Filter by brand",
            options=[None] + brands,
            format_func=lambda x: "All brands" if x is None else x,
        )
    with col2:
        filter_category = st.selectbox(
            "Filter by category",
            options=[None] + categories,
            format_func=lambda x: "All categories" if x is None else x,
        )
    rows = get_current_prices(
        brand_name=filter_brand if filter_brand else None,
        category=filter_category if filter_category else None,
    )
    if not rows:
        st.info("No price data yet. Go to the **Run scrape** tab to fetch competitor prices.")
    else:
        import pandas as pd
        df = pd.DataFrame(rows)
        df["Last updated"] = df["scraped_at"].dt.strftime("%Y-%m-%d %H:%M")
        display_df = df[["brand_name", "product_name", "category", "price", "currency", "Last updated"]]
        display_df = display_df.rename(columns={
            "brand_name": "Brand",
            "product_name": "Product",
            "category": "Category",
            "price": "Price",
            "currency": "Currency",
        })
        st.dataframe(display_df, use_container_width=True, hide_index=True)

with tab2:
    st.header("Price history")
    st.caption("Select one or more products to see how their price changed over time.")
    product_options = get_products_for_selector()
    if not product_options:
        st.info("No products in the database yet. Run a scrape first.")
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

with tab3:
    st.header("Run scrape now")
    scrape_password = _get_scrape_password()
    can_run_scrape = not scrape_password or st.session_state.is_admin
    if not can_run_scrape:
        st.info(
            "Only the admin can update data. Enter the admin password in the **sidebar** to run a scrape."
        )
    else:
        st.caption(
            "Fetch current prices from Spanx, SKIMS, and Honeylove. "
            "This may take a minute. New prices will be stored and shown in the other tabs."
        )
        if st.button("Execute scrape"):
            with st.spinner("Scraping competitor sites…"):
                try:
                    items, products_updated, price_records = run_all_scrapers(save=True)
                    st.success(
                        f"Done. Processed **{len(items)}** items: "
                        f"**{products_updated}** products updated, **{price_records}** price records saved."
                    )
                except Exception as e:
                    st.error(f"Scrape failed: {e}")
