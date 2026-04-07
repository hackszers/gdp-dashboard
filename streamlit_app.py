import streamlit as st
import pandas as pd
from datetime import timedelta
import re

# --- Page Config ---
st.set_page_config(page_title="Roblox Analytics", layout="wide", page_icon="📊")
st.title("📊 Roblox Sales Dashboard - Her Revenue After Split")

# --- Sidebar ---
st.sidebar.subheader("DevEx Settings")
devex_rate = st.sidebar.number_input(
    "Exchange Rate (USD per 1 R$)",
    value=0.0038,
    format="%.4f"
)

uploaded_files = st.file_uploader(
    "Upload Sales CSVs (multiple allowed)",
    type=["csv"],
    accept_multiple_files=True
)

# ====================== RULES ======================
SPECIAL_CAPE_GROUP = 32600641

ALLOWED_CAPE_ASSET_IDS = {
    82121186934297, 109090921647450, 126346507087936,
    14426328438, 14426332963, 14426354335,
    14424958183, 14424953018, 14424945182,
    14343293342, 14343305312, 14343308456, 14343298093,
    14434910968, 14434895327, 14434915218,
    14434890711, 14434904829
}

FIFTY_PERCENT_GROUPS = {823805908}
FULL_REVENUE_GROUPS = {13860593, 33024439, 35387713}

# --- DATA LOADER ---
@st.cache_data
def load_data(files):
    df_list = []
    for file in files:
        temp_df = pd.read_csv(file)
        temp_df.columns = [c.strip() for c in temp_df.columns]
        # Try to detect if this is a Cape Group file from filename
        if hasattr(file, 'name') and '32600641' in file.name:
            temp_df['Group Id'] = SPECIAL_CAPE_GROUP
        df_list.append(temp_df)
    return pd.concat(df_list, ignore_index=True)

if uploaded_files:
    try:
        df = load_data(uploaded_files)

        # Column detection
        date_col = next((c for c in ['Date and Time', 'Created', 'Date'] if c in df.columns), None)
        rev_col = next((c for c in ['Revenue', 'Net Revenue', 'Amount', 'Robux Earned'] if c in df.columns), None)
        asset_col = next((c for c in ['Asset Id', 'Asset ID', 'AssetId', 'AssetID'] if c in df.columns), None)
        name_col = next((c for c in ['Asset Name', 'Name'] if c in df.columns), None)

        if not date_col or not rev_col:
            st.error(f"Missing required columns. Found: {list(df.columns)}")
            st.stop()

        # Clean data
        df[rev_col] = pd.to_numeric(df[rev_col].astype(str).str.replace(r"[^\d.-]", "", regex=True), errors='coerce')
        df = df.dropna(subset=[rev_col])

        if asset_col:
            df[asset_col] = pd.to_numeric(df[asset_col], errors='coerce')

        df[date_col] = pd.to_datetime(df[date_col], utc=True, errors='coerce')
        df = df.dropna(subset=[date_col])

        now = pd.Timestamp.now("UTC")

        # ====================== HER SHARE CALCULATION ======================
        def get_her_share(row):
            revenue = row[rev_col]
            asset_id = row.get(asset_col)

            # Force Cape Group logic if Group Id was added from filename
            group = row.get('Group Id', 0)

            if group == SPECIAL_CAPE_GROUP or (pd.notna(asset_id) and asset_id in ALLOWED_CAPE_ASSET_IDS):
                if pd.notna(asset_id) and int(asset_id) in ALLOWED_CAPE_ASSET_IDS:
                    return revenue * 0.5
                else:
                    return 0.0

            elif group in FIFTY_PERCENT_GROUPS:
                return revenue * 0.5

            else:
                return revenue

        df['Her Robux'] = df.apply(get_her_share, axis=1).round(0)
        df['Her USD'] = df['Her Robux'] * devex_rate

        # ====================== DEBUG ======================
        st.sidebar.subheader("Debug Info")
        st.sidebar.write(f"**Files Uploaded:** {len(uploaded_files)}")
        st.sidebar.write(f"**Total Rows:** {len(df)}")
        if 'Group Id' in df.columns:
            st.sidebar.write(f"**Cape Group Rows:** {(df['Group Id'] == SPECIAL_CAPE_GROUP).sum()}")

        # Show how many capes are allowed vs ignored
        if asset_col:
            cape_mask = df[asset_col].isin(ALLOWED_CAPE_ASSET_IDS)
            st.subheader(f"✅ Allowed Capes (50% Share): {cape_mask.sum():,} sales")
            st.subheader(f"❌ Ignored Capes (0% Share): {(~cape_mask).sum():,} sales")

        # ====================== DATE FILTER ======================
        st.sidebar.subheader("Date Filter")
        min_date = df[date_col].min().date()
        max_date = df[date_col].max().date()
        date_range = st.sidebar.date_input("Select Date Range", [min_date, max_date])

        if len(date_range) == 2:
            start_date, end_date = date_range
            df = df[(df[date_col].dt.date >= start_date) & (df[date_col].dt.date <= end_date)]

        # ====================== METRICS ======================
        st.subheader("💰 Her Revenue Summary (After Split)")
        total_her_robux = int(df['Her Robux'].sum())
        total_her_usd = total_her_robux * devex_rate

        col1, col2 = st.columns(2)
        col1.metric("Total Her Robux", f"R$ {total_her_robux:,}")
        col2.metric("Estimated DevEx (Her Share)", f"${total_her_usd:,.2f}")

        # Top Assets
        st.divider()
        st.subheader("🏆 Top Assets - Her Share")
        if name_col and asset_col:
            top = df.groupby([name_col, asset_col])['Her Robux'].sum().reset_index()
            top = top.sort_values('Her Robux', ascending=False)
            top['Her USD'] = top['Her Robux'] * devex_rate
            st.dataframe(top.head(30).style.format({"Her Robux": "{:,.0f}", "Her USD": "${:,.2f}"}))

        st.download_button(
            "📥 Download Data with Her Share",
            df.to_csv(index=False),
            file_name="her_revenue_split.csv"
        )

    except Exception as e:
        st.error("App crashed")
        st.exception(e)
