import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import requests

# --- Dashboard Configuration ---
st.set_page_config(page_title="Roblox Group Analytics", layout="wide")
st.title("📊 Roblox Sales Dashboard")

# Sidebar for Group ID
group_id = st.sidebar.text_input("Enter Roblox Group ID", value="")

# --- Step 1: CSV Upload ---
uploaded_file = st.file_uploader("Upload your 'Sale of Goods' CSV file", type=["csv"])

if uploaded_file is not None:
    # Read the CSV and clean column names
    df = pd.read_csv(uploaded_file)
    df.columns = [c.strip() for c in df.columns]
    
    # Handle Roblox date format
    df['Created'] = pd.to_datetime(df['Created'])
    
    now = datetime.now()
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # Filter for time periods
    daily_df = df[df['Created'] >= day_ago]
    weekly_df = df[df['Created'] >= week_ago]
    monthly_df = df[df['Created'] >= month_ago]

    # Show Earnings Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Past 24 Hours", f"R$ {int(daily_df['Net Revenue'].sum()):,}")
    col2.metric("Past 7 Days", f"R$ {int(weekly_df['Net Revenue'].sum()):,}")
    col3.metric("Past 30 Days", f"R$ {int(monthly_df['Net Revenue'].sum()):,}")

    st.divider()
    st.subheader("🏆 Top Selling Items (from CSV)")
    
    # Calculate best sellers
    best_sellers = df.groupby('Item').agg({
        'Net Revenue': 'sum',
        'Item': 'count'
    }).rename(columns={'Item': 'Total Sales'}).sort_values(by='Total Sales', ascending=False)

    st.table(best_sellers.head(20))

# --- Step 2: Live Group Info ---
if group_id:
    st.sidebar.markdown("---")
    try:
        api_url = f"https://catalog.roblox.com/v1/search/items/details?Category=3&CreatorTargetId={group_id}&CreatorType=2"
        r = requests.get(api_url)
        if r.status_code == 200:
            items = r.json().get('data', [])
            st.sidebar.success(f"📦 Items currently for sale: {len(items)}")
    except:
        st.sidebar.error("API Connection Error")
