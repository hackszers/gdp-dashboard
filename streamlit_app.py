import os, subprocess, sys
import streamlit as st
import pandas as pd
import requests
from datetime import timedelta

# --- Page Config ---
st.set_page_config(page_title="Roblox Analytics", layout="wide", page_icon="📊")
st.title("📊 Roblox Sales Dashboard")

# --- Sidebar ---
group_id = st.sidebar.text_input("Enter Roblox Group ID", value="823805908")

st.sidebar.divider()
st.sidebar.subheader("DevEx Settings")

# ✅ Updated DevEx rate
devex_rate = st.sidebar.number_input(
    "Exchange Rate (USD/1 R$)",
    value=0.0038,
    format="%.4f"
)

# ✅ MULTI FILE UPLOAD
uploaded_files = st.file_uploader(
    "Upload 'Sale of Goods' CSVs",
    type=["csv"],
    accept_multiple_files=True
)

# --- DATA LOADER ---
@st.cache_data
def load_data(files):
    df_list = []
    for file in files:
        temp_df = pd.read_csv(file)
        temp_df.columns = [c.strip() for c in temp_df.columns]
        df_list.append(temp_df)
    return pd.concat(df_list, ignore_index=True)

if uploaded_files:
    try:
        df = load_data(uploaded_files)

        # --- COLUMN DETECTION ---
        possible_date_cols = ['Date and Time', 'Created', 'Date']
        possible_rev_cols = ['Revenue', 'Net Revenue', 'Amount', 'Robux Earned']
        possible_item_cols = ['Asset Name', 'Item', 'Name']

        date_col = next((c for c in possible_date_cols if c in df.columns), None)
        rev_col = next((c for c in possible_rev_cols if c in df.columns), None)
        item_col = next((c for c in possible_item_cols if c in df.columns), None)

        if not date_col or not rev_col:
            st.error(f"❌ Required columns not found.\n\nColumns detected: {list(df.columns)}")
            st.stop()

        # ✅ CLEAN & CONVERT REVENUE COLUMN
        df[rev_col] = (
            df[rev_col]
            .astype(str)
            .str.replace(r"[^\d.-]", "", regex=True)
        )
        df[rev_col] = pd.to_numeric(df[rev_col], errors='coerce')
        df = df.dropna(subset=[rev_col])

        # ✅ DATETIME FIX (Pandas 3.x/4.x compatible)
        df[date_col] = pd.to_datetime(df[date_col], utc=True, errors='coerce')
        df = df.dropna(subset=[date_col])

        # ✅ CRITICAL FIX: Changed from .utcnow() to .now('UTC')
        now = pd.Timestamp.now('UTC')

        # --- DATE FILTER ---
        st.sidebar.subheader("Date Filter")

        min_date = df[date_col].min().date()
        max_date = df[date_col].max().date()

        date_range = st.sidebar.date_input(
            "Select Date Range",
            [min_date, max_date]
        )

        if len(date_range) == 2:
            start_date, end_date = date_range
            df = df[
                (df[date_col].dt.date >= start_date) &
                (df[date_col].dt.date <= end_date)
            ]

        # --- TIME FILTERS ---
        today_val = now.date()
        df_today = df[df[date_col].dt.date == today_val]
        df_yesterday = df[df[date_col].dt.date == (today_val - timedelta(days=1))]
        df_7d = df[df[date_col] >= (now - timedelta(days=7))]
        df_31d = df[df[date_col] >= (now - timedelta(days=31))]
        df_all = df.copy()

        # --- METRICS ---
        st.subheader("💰 Revenue Summary")

        c1, c2, c3, c4, c5 = st.columns(5)
        periods = [
            ("Today", df_today),
            ("Yesterday", df_yesterday),
            ("7 Days", df_7d),
            ("31 Days", df_31d),
            ("All Time", df_all)
        ]

        for col, (label, data) in zip([c1, c2, c3, c4, c5], periods):
            robux_sum = int(data[rev_col].sum())
            usd_val = robux_sum * devex_rate
            col.metric(label, f"R$ {robux_sum:,}")
            col.write(f"**Est. DevEx:** ${usd_val:,.2f}")

        # --- BEST SELLER TODAY ---
        if not df_today.empty and item_col:
            best_today = df_today.groupby(item_col)[rev_col].sum().idxmax()
            st.success(f"🔥 Best Seller Today: {best_today}")

        # --- DAILY REVENUE ---
        st.divider()
        st.subheader("📊 Daily Revenue")

        daily = df.groupby(df[date_col].dt.date)[rev_col].sum()
        st.bar_chart(daily)

        # --- TREND ---
        st.divider()
        st.subheader("📈 Revenue Trend (All Time)")

        chart_data = df.copy()
        chart_data['Date'] = chart_data[date_col].dt.date

        if item_col:
            top_5_names = df.groupby(item_col)[rev_col].sum().nlargest(5).index.tolist()

            pivot_df = chart_data.pivot_table(
                index='Date',
                columns=item_col,
                values=rev_col,
                aggfunc='sum'
            ).fillna(0)

            main_cols = [c for c in pivot_df.columns if c in top_5_names]
            other_cols = [c for c in pivot_df.columns if c not in top_5_names]

            final_chart = pivot_df[main_cols].copy()

            if other_cols:
                final_chart['Other Assets'] = pivot_df[other_cols].sum(axis=1)

            st.line_chart(final_chart)
        else:
            st.line_chart(daily)

        # --- TOP ITEMS ---
        st.divider()
        st.subheader("🏆 Top Selling Assets")

        if item_col:
            top_items = df.groupby(item_col).agg({
                rev_col: 'sum',
                item_col: 'count'
            }).rename(columns={
                item_col: 'Sales',
                rev_col: 'Total Robux'
            })

            top_items['Est. USD'] = (top_items['Total Robux'] * devex_rate).round(2)

            # ✅ STYLING FIX: Updated format syntax for Pandas 3/4
            st.table(
                top_items.sort_values('Total Robux', ascending=False)
                .head(15)
                .style.format(precision=2, thousands=",")
            )

        # --- DOWNLOAD ---
        st.download_button(
            "📥 Download Clean Data",
            df.to_csv(index=False),
            file_name="cleaned_roblox_sales.csv"
        )

    except Exception as e:
        st.error(f"Error: {e}")

# --- GROUP INFO ---
if group_id:
    try:
        r = requests.get(f"https://catalog.roblox.com/v1/search/items/details?Category=3&CreatorTargetId={group_id}&CreatorType=2")
        if r.status_code == 200:
            st.sidebar.success(f"📦 Recent Items Found: {len(r.json().get('data', []))}")
    except:
        pass
