import os
import subprocess
import sys

# --- AUTO-INSTALLER ---
def install(package):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    except:
        pass

try:
    import pandas as pd
    import requests
except ImportError:
    install('pandas')
    install('requests')
    import pandas as pd
    import requests

import streamlit as st
from datetime import datetime, timedelta

# --- Dashboard Configuration ---
st.set_page_config(page_title="Roblox Group Analytics", layout="wide")
st.title("📊 Roblox Sales Dashboard")

# Sidebar for Group ID
group_id = st.sidebar.text_input("Enter Roblox Group ID", value="")

# --- Step 1: CSV Upload ---
uploaded_file = st.file_uploader("Upload your 'Sale of Goods' CSV file", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        df.columns = [c.strip() for c in df.columns]

        # 2026 Column Detection based on YOUR file
        # Added 'Date and Time' to the list
        date_options = ['Date and Time', 'Sale Date and Time', 'Created', 'Date']
        rev_options = ['Revenue', 'Net Revenue', 'Robux']
        item_options = ['Asset Name', 'Item', 'Product']

        date_col = next((c for c in date_options if c in df.columns), None)
        rev_col = next((c for c in rev_options if c in df.columns), None)
        item_col = next((c for c in item_options if c in df.columns), None)

        if not date_col or not rev_col:
            st.error(f"Missing required columns! Found: {list(df.columns)}")
            st.stop()

        # Convert date column
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=[date_col])

        # Time calculations
        now = datetime.now(df[date_col].dt.tz)
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        # Show Metrics
        st.subheader("💰 Earnings Summary")
        col1, col2, col3 = st.columns(3)
        
        d_sum = df[df[date_col] >= day_ago][rev_col].sum()
        w_sum = df[df[date_col] >= week_ago][rev_col].sum()
        m_sum = df[df[date_col] >= month_ago][rev_col].sum()

        col1.metric("Past 24 Hours", f"R$ {int(d_sum):,}")
        col2.metric("Past 7 Days", f"R$ {int(w_sum):,}")
        col3.metric("Past 30 Days", f"R$ {int(m_sum):,}")

        st.divider()
        
        if item_col:
            st.subheader("🏆 Top Selling Items")
            best_sellers = df.groupby(item_col).agg({
                rev_col: 'sum',
                item_col: 'count'
            }).rename(columns={item_col: 'Sales', rev_col: 'Total Robux'}).sort_values(by='Sales', ascending=False)
            st.table(best_sellers.head(20))
            
    except Exception as e:
        st.error(f"Error: {e}")

# --- Step 2: Live Group Info ---
if group_id:
    st.sidebar.markdown("---")
    try:
        r = requests.get(f"https://catalog.roblox.com/v1/search/items/details?Category=3&CreatorTargetId={group_id}&CreatorType=2")
        if r.status_code == 200:
            st.sidebar.success(f"📦 Items for sale: {len(r.json().get('data', []))}")
    except:
        pass
