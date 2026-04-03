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
st.set_page_config(page_title="Roblox Analytics", layout="wide", page_icon="📊")
st.title("📊 Roblox Sales Dashboard")

# --- Sidebar ---
group_id = st.sidebar.text_input("Enter Roblox Group ID", value="823805908")

st.sidebar.divider()
st.sidebar.subheader("DevEx Settings")
# Standard DevEx rate
devex_rate = st.sidebar.number_input("Exchange Rate (USD/1 R$)", value=0.0035, format="%.4f")

uploaded_file = st.file_uploader("Upload 'Sale of Goods' CSV", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        df.columns = [c.strip() for c in df.columns]

        date_col = 'Date and Time' if 'Date and Time' in df.columns else 'Created'
        rev_col = 'Revenue' if 'Revenue' in df.columns else 'Net Revenue'
        item_col = 'Asset Name' if 'Asset Name' in df.columns else 'Item'

        if date_col in df.columns and rev_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            df = df.dropna(subset=[date_col])
            
            now = datetime.now(df[date_col].dt.tz) if df[date_col].dt.tz else datetime.now()
            
            # Filters
            df_today = df[df[date_col].dt.date == now.date()]
            df_yesterday = df[df[date_col].dt.date == (now.date() - timedelta(days=1))]
            df_7d = df[df[date_col] >= (now - timedelta(days=7))]
            df_31d = df[df[date_col] >= (now - timedelta(days=31))]

            # --- TOP METRICS ---
            st.subheader("💰 Revenue Summary")
            c1, c2, c3, c4 = st.columns(4)
            periods = [("Today", df_today), ("Yesterday", df_yesterday), ("7 Days", df_7d), ("31 Days", df_31d)]
            cols = [c1, c2, c3, c4]
            
            for i, (label, data) in enumerate(periods):
                robux_sum = int(data[rev_col].sum())
                usd_val = robux_sum * devex_rate
                cols[i].metric(label, f"R$ {robux_sum:,}")
                cols[i].write(f"**Est. USD:** ${usd_val:,.2f}")

            # --- MULTI-LINE TREND (PHOTO STYLE) ---
            st.divider()
            st.subheader("📈 31-Day Revenue Trend")

            # Get Top 5 Items
            top_5_names = df_31d.groupby(item_col)[rev_col].sum().nlargest(5).index.tolist()

            # Prepare Chart Data
            chart_data = df_31d.copy()
            chart_data['Date'] = chart_data[date_col].dt.date
            
            # Create a pivot table: Rows = Date, Columns = Asset Names, Values = Revenue
            pivot_df = chart_data.pivot_table(index='Date', columns=item_col, values=rev_col, aggfunc='sum').fillna(0)
            
            # Keep only Top 5 and group the rest as 'Others'
            main_cols = [c for c in pivot_df.columns if c in top_5_names]
            other_cols = [c for c in pivot_df.columns if c not in top_5_names]
            
            final_chart = pivot_df[main_cols].copy()
            if other_cols:
                final_chart['Other Assets'] = pivot_df[other_cols].sum(axis=1)
            
            # Display the multi-colored area chart
            st.area_chart(final_chart)

            # --- TABLE ---
            st.divider()
            st.subheader("🏆 Top Selling Assets")
            top_items = df_31d.groupby(item_col).agg({rev_col: 'sum', item_col: 'count'}).rename(columns={item_col: 'Sales', rev_col: 'Total Robux'})
            top_items['Est. USD'] = (top_items['Total Robux'] * devex_rate).round(2)
            st.table(top_items.sort_values('Total Robux', ascending=False).head(15).style.format("{:,.2f}"))

    except Exception as e:
        st.error(f"Error: {e}")

# Sidebar Group Info
if group_id:
    try:
        r = requests.get(f"https://catalog.roblox.com/v1/search/items/details?Category=3&CreatorTargetId={group_id}&CreatorType=2")
        if r.status_code == 200:
            st.sidebar.success(f"📦 Recent Items: {len(r.json().get('data', []))}")
    except: pass
