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

# --- Page Config ---
st.set_page_config(page_title="Roblox Analytics", layout="wide")
st.title("📊 Roblox Sales Dashboard")

group_id = st.sidebar.text_input("Enter Roblox Group ID", value="823805908")
uploaded_file = st.file_uploader("Upload 'Sale of Goods' CSV", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        df.columns = [c.strip() for c in df.columns]

        # Column Mapping
        date_col = 'Date and Time' if 'Date and Time' in df.columns else 'Created'
        rev_col = 'Revenue' if 'Revenue' in df.columns else 'Net Revenue'
        item_col = 'Asset Name' if 'Asset Name' in df.columns else 'Item'

        if date_col in df.columns and rev_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            df = df.dropna(subset=[date_col])
            
            # --- DATE CALCULATIONS ---
            # Using .date() to get full-day accuracy
            now = datetime.now(df[date_col].dt.tz)
            today_date = now.date()
            yesterday_date = today_date - timedelta(days=1)
            
            # Filter Dataframes
            df_today = df[df[date_col].dt.date == today_date]
            df_yesterday = df[df[date_col].dt.date == yesterday_date]
            df_7d = df[df[date_col] >= (now - timedelta(days=7))]
            df_31d = df[df[date_col] >= (now - timedelta(days=31))]

            # --- TOP METRICS ---
            st.subheader("💰 Revenue Summary")
            c1, c2, c3, c4 = st.columns(4)
            
            c1.metric("Today", f"R$ {int(df_today[rev_col].sum()):,}")
            c2.metric("Yesterday", f"R$ {int(df_yesterday[rev_col].sum()):,}")
            c3.metric("Past 7 Days", f"R$ {int(df_7d[rev_col].sum()):,}")
            c4.metric("Past 31 Days", f"R$ {int(df_31d[rev_col].sum()):,}")

            # --- TREND CHART ---
            st.divider()
            st.subheader("📈 31-Day Trend")
            chart_data = df_31d.copy()
            chart_data['Day'] = chart_data[date_col].dt.date
            daily_rev = chart_data.groupby('Day')[rev_col].sum()
            st.area_chart(daily_rev)

            # --- TOP ITEMS TABLE ---
            st.divider()
            st.subheader("🏆 Top Selling Assets")
            top_items = df.groupby(item_col).agg({
                rev_col: 'sum',
                item_col: 'count'
            }).rename(columns={item_col: 'Sales', rev_col: 'Total Robux'})
            
            top_items['Total Robux'] = top_items['Total Robux'].astype(int)
            top_items = top_items.sort_values(by='Total Robux', ascending=False)
            
            st.table(top_items.head(15).style.format("{:,}"))
            
    except Exception as e:
        st.error(f"Processing... please refresh in 10s. (Error: {e})")

# Sidebar Info
if group_id:
    try:
        r = requests.get(f"https://catalog.roblox.com/v1/search/items/details?Category=3&CreatorTargetId={group_id}&CreatorType=2")
        if r.status_code == 200:
            count = len(r.json().get('data', []))
            st.sidebar.success(f"📦 Recent Items: {count}")
    except: pass
