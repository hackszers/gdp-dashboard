import streamlit as st
import pandas as pd
from datetime import timedelta

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

# Only these Asset IDs in the Cape group are counted (50%)
ALLOWED_CAPE_ASSET_IDS = {
    82121186934297, 109090921647450, 126346507087936,
    14426328438, 14426332963, 14426354335,
    14424958183, 14424953018, 14424945182,
    14343293342, 14343305312, 14343308456, 14343298093,
    14434910968, 14434895327, 14434915218,
    14434890711, 14434904829
}

FIFTY_PERCENT_GROUPS = {823805908}   # FACIN - 50% on everything
FULL_REVENUE_GROUPS = {13860593, 33024439, 35387713}  # Trippy Fashion, 3D, Hair

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

        # Column detection
        date_col = next((c for c in ['Date and Time', 'Created', 'Date'] if c in df.columns), None)
        rev_col = next((c for c in ['Revenue', 'Net Revenue', 'Amount', 'Robux Earned'] if c in df.columns), None)
        asset_col = next((c for c in ['Asset Id', 'Asset ID', 'AssetId', 'AssetID'] if c in df.columns), None)

        # Improved Group ID detection
        group_col = next((c for c in ['Group Id', 'Group ID', 'GroupId', 'group_id', 'Group'] 
                         if c in df.columns), None)

        if not date_col or not rev_col:
            st.error(f"Missing required columns. Found: {list(df.columns)}")
            st.stop()

        # Clean Revenue
        df[rev_col] = pd.to_numeric(
            df[rev_col].astype(str).str.replace(r"[^\d.-]", "", regex=True),
            errors='coerce'
        )
        df = df.dropna(subset=[rev_col])

        # Clean Asset Id
        if asset_col:
            df[asset_col] = pd.to_numeric(df[asset_col], errors='coerce')

        # Datetime
        df[date_col] = pd.to_datetime(df[date_col], utc=True, errors='coerce')
        df = df.dropna(subset=[date_col])

        now = pd.Timestamp.now("UTC")

        # ====================== HER SHARE CALCULATION (Fixed) ======================
        def get_her_share(row):
            # Get group safely
            if group_col and group_col in row:
                try:
                    group = int(row[group_col])
                except (ValueError, TypeError):
                    group = 0
            else:
                group = 0

            revenue = row[rev_col]
            asset_id = row.get(asset_col) if asset_col else None

            if group == SPECIAL_CAPE_GROUP:
                # Only specific capes get 50%, everything else in this group = 0
                if pd.notna(asset_id) and int(asset_id) in ALLOWED_CAPE_ASSET_IDS:
                    return revenue * 0.5
                else:
                    return 0  # Ignore other capes in the special group

            elif group in FIFTY_PERCENT_GROUPS:
                return revenue * 0.5

            else:
                # 100% for Trippy groups and any other groups she fully owns
                return revenue

        df['Her Robux'] = df.apply(get_her_share, axis=1)
        df['Her USD'] = df['Her Robux'] * devex_rate

        # ====================== DEBUG INFO ======================
        st.sidebar.subheader("Debug Info")
        st.sidebar.write(f"**Group Column Detected:** {group_col}")
        if group_col:
            unique_groups = df[group_col].dropna().unique()
            st.sidebar.write(f"Unique Groups Found: {len(unique_groups)}")
            st.sidebar.write(unique_groups[:10])  # Show first 10

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

        # Period metrics
        cols = st.columns(4)
        periods = [
            ("Today", df[df[date_col].dt.date == now.date()]),
            ("7 Days", df[df[date_col] >= (now - timedelta(days=7))]),
            ("31 Days", df[df[date_col] >= (now - timedelta(days=31))]),
            ("All Time", df)
        ]

        for col, (label, data) in zip(cols, periods):
            robux = int(data['Her Robux'].sum())
            usd = robux * devex_rate
            col.metric(label, f"R$ {robux:,}")
            col.write(f"**USD:** ${usd:,.2f}")

        st.divider()
        st.subheader("📊 Daily Her Revenue")
        daily = df.groupby(df[date_col].dt.date)['Her Robux'].sum()
        st.bar_chart(daily)

        # Top Assets (Her Share)
        st.divider()
        st.subheader("🏆 Top Assets - Her Share")
        if asset_col and 'Asset Name' in df.columns:
            top = df.groupby(['Asset Name', asset_col]).agg({
                'Her Robux': 'sum'
            }).sort_values('Her Robux', ascending=False)
            top['Her USD'] = top['Her Robux'] * devex_rate
            st.dataframe(top.head(20).style.format({"Her Robux": "{:,.0f}", "Her USD": "${:,.2f}"}))

        # Download
        st.download_button(
            "📥 Download Data with Her Share",
            df.to_csv(index=False),
            file_name="her_revenue_split.csv"
        )

    except Exception as e:
        st.error("App crashed")
        st.exception(e)
