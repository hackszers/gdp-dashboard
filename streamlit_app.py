import os, subprocess, sys
import streamlit as st

# --- AUTO-INSTALLER ---
def install(package):
    try: subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    except: pass

try:
    import pandas as pd
    import requests
except ImportError:
    install('pandas')
    install('requests')
    import pandas as pd
    import requests

from datetime import datetime, timedelta

# --- Page Setup ---
st.set_page_config(page_title="Roblox Analytics", layout="wide")
st.title("🚀 Roblox Sales Pro Dashboard")

group_id = st.sidebar.text_input("Enter Roblox Group ID", value="")
uploaded_file = st.file_uploader("Upload 'Sale of Goods' CSV", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        df.columns = [c.strip() for c in df.columns]

        # Column Mapping
        date_col = next((c for c in ['Date and Time', 'Sale Date and Time', 'Created'] if c in df.columns), None)
        rev_col = next((c for c in ['Revenue', 'Net Revenue'] if c in df.columns), None)
        item_col = next((c for c in ['Asset Name', 'Item'] if c in df.columns), None)

        if date_col and rev_col:
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            df = df.dropna(subset=[date_col])
            
            # --- CALCULATE METRICS ---
            now = datetime.now(df[date_col].dt.tz)
            d_sum = df[df[date_col] >= (now - timedelta(days=1))][rev_col].sum()
            w_sum = df[df[date_col] >= (now - timedelta(days=7))][rev_col].sum()
            m_sum = df[df[date_col] >= (now - timedelta(days=30))][rev_col].sum()

            st.subheader("💰 Revenue Summary")
            c1, c2, c3 = st.columns(3)
            c1.metric("24 Hours", f"R$ {int(d_sum):,}")
            c2.metric("7 Days", f"R$ {int(w_sum):,}")
            c3.metric("30 Days", f"R$ {int(m_sum):,}")

            # --- SALES CHART ---
            st.divider()
            st.subheader("📈 Revenue Trend (Last 30 Days)")
            chart_data = df[df[date_col] >= (now - timedelta(days=30))].copy()
            chart_data['Day'] = chart_data[date_col].dt.date
            daily_trend = chart_data.groupby('Day')[rev_col].sum()
            st.line_chart(daily_trend)

            # --- TOP ITEMS TABLE ---
            if item_col:
                st.divider()
                st.subheader("🏆 Top Selling Assets")
                top_items = df.groupby(item_col).agg({
                    rev_col: 'sum',
                    item_col: 'count'
                }).rename(columns={item_col: 'Sales Count', rev_col: 'Total Robux'})
                
                # Clean up formatting: make Robux an integer (no decimals)
                top_items['Total Robux'] = top_items['Total Robux'].astype(int)
                top_items = top_items.sort_values(by='Total Robux', ascending=False)
                
                st.table(top_items.head(15).style.format("{:,}"))
            
    except Exception as e:
        st.error(f"Error: {e}")

# Sidebar Info
if group_id:
    try:
        r = requests.get(f"https://catalog.roblox.com/v1/search/items/details?Category=3&CreatorTargetId={group_id}&CreatorType=2")
        if r.status_code == 200:
            st.sidebar.success(f"📦 Active Items: {len(r.json().get('data', []))}")
    except: pass
