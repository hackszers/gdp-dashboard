import os, subprocess, sys
import streamlit as st

# --- AUTO-INSTALLER (Only the basics) ---
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

# --- Page Config ---
st.set_page_config(page_title="Roblox Analytics", layout="wide")
st.title("📊 Roblox Sales Dashboard")

group_id = st.sidebar.text_input("Enter Roblox Group ID", value="823805908")
uploaded_file = st.file_uploader("Upload 'Sale of Goods' CSV", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        df.columns = [c.strip() for c in df.columns]

        # Map columns from your specific CSV
        date_col = 'Date and Time' if 'Date and Time' in df.columns else 'Created'
        rev_col = 'Revenue' if 'Revenue' in df.columns else 'Net Revenue'
        item_col = 'Asset Name' if 'Asset Name' in df.columns else 'Item'

        if date_col in df.columns and rev_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            df = df.dropna(subset=[date_col])
            
            # --- TOP METRICS ---
            now = datetime.now(df[date_col].dt.tz)
            st.subheader("💰 Revenue Summary")
            c1, c2, c3 = st.columns(3)
            
            d_sum = df[df[date_col] >= (now - timedelta(days=1))][rev_col].sum()
            w_sum = df[df[date_col] >= (now - timedelta(days=7))][rev_col].sum()
            m_sum = df[df[date_col] >= (now - timedelta(days=30))][rev_col].sum()

            c1.metric("Past 24h", f"R$ {int(d_sum):,}")
            c2.metric("Past 7d", f"R$ {int(w_sum):,}")
            c3.metric("Past 30d", f"R$ {int(m_sum):,}")

            # --- TREND CHART (Static/No-Scroll) ---
            st.divider()
            st.subheader("📈 30-Day Trend")
            chart_data = df[df[date_col] >= (now - timedelta(days=30))].copy()
            chart_data['Day'] = chart_data[date_col].dt.date
            daily_rev = chart_data.groupby('Day')[rev_col].sum()
            
            # Use area_chart (better looking, and we lock it with a simple display)
            st.area_chart(daily_rev)

            # --- TOP ITEMS TABLE ---
            st.divider()
            st.subheader("🏆 Top Selling Assets")
            top_items = df.groupby(item_col).agg({
                rev_col: 'sum',
                item_col: 'count'
            }).rename(columns={item_col: 'Sales', rev_col: 'Total Robux'})
            
            # Clean decimals and format
            top_items['Total Robux'] = top_items['Total Robux'].astype(int)
            top_items = top_items.sort_values(by='Total Robux', ascending=False)
            
            st.table(top_items.head(15).style.format("{:,}"))
            
    except Exception as e:
        st.error(f"Waiting for tools to install... please refresh in 10 seconds. (Error: {e})")

# Sidebar Info
if group_id:
    try:
        r = requests.get(f"https://catalog.roblox.com/v1/search/items/details?Category=3&CreatorTargetId={group_id}&CreatorType=2")
        if r.status_code == 200:
            count = len(r.json().get('data', []))
            st.sidebar.success(f"📦 Active Items: {count}")
    except: pass
