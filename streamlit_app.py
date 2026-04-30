import streamlit as st
import pandas as pd
import altair as alt
import numpy as np

# --- Page Config ---
st.set_page_config(page_title="Roblox Analytics", layout="wide", page_icon="📊")
st.title("📊 Roblox Sales Dashboard - Gross vs. Her Revenue")

# ====================== CONSTANTS ======================
DEVEX_RATE = 0.0038
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

# ====================== FILE UPLOAD ======================
uploaded_files = st.file_uploader(
    "Upload Sales CSVs",
    type=["csv"],
    accept_multiple_files=True
)

# ====================== LOAD DATA ======================
@st.cache_data
def load_data(files):
    df_list = []

    for file in files:
        temp_df = pd.read_csv(file)
        temp_df.columns = [c.strip() for c in temp_df.columns]

        if 'Group Id' not in temp_df.columns:
            temp_df['Group Id'] = 0

        # Filename Detection Logic
        name = file.name
        if '32600641' in name: temp_df['Group Id'] = 32600641
        elif '823805908' in name: temp_df['Group Id'] = 823805908
        elif '13860593' in name: temp_df['Group Id'] = 13860593
        elif '33024439' in name: temp_df['Group Id'] = 33024439
        elif '35387713' in name: temp_df['Group Id'] = 35387713

        df_list.append(temp_df)

    if not df_list: return None, 0, None, None, None, None
    
    df = pd.concat(df_list, ignore_index=True)

    # Detect Columns
    date_col = next((c for c in ['Date and Time', 'Created', 'Date'] if c in df.columns), None)
    rev_col = next((c for c in ['Revenue', 'Net Revenue', 'Amount', 'Robux Earned'] if c in df.columns), None)
    asset_col = next((c for c in ['Asset Id', 'Asset ID', 'AssetId'] if c in df.columns), None)
    name_col = next((c for c in ['Asset Name', 'Name'] if c in df.columns), None)

    # Deduplication
    dedupe_cols = [col for col in [date_col, rev_col, asset_col, name_col, 'Group Id'] if col]
    before = len(df)
    df = df.drop_duplicates(subset=dedupe_cols, keep='first')
    duplicates_removed = before - len(df)

    return df, duplicates_removed, date_col, rev_col, asset_col, name_col

# ====================== MAIN ======================
if uploaded_files:
    df, duplicates_removed, date_col, rev_col, asset_col, name_col = load_data(uploaded_files)

    if duplicates_removed > 0:
        st.warning(f"⚠️ Removed {duplicates_removed:,} duplicate rows")

    if not date_col or not rev_col:
        st.error("Missing required columns (Date or Revenue)")
        st.stop()

    # --- Clean Data ---
    df[rev_col] = pd.to_numeric(df[rev_col].astype(str).str.replace(r"[^\d.-]", "", regex=True), errors='coerce')
    df[date_col] = pd.to_datetime(df[date_col], utc=True, errors='coerce')
    df = df.dropna(subset=[rev_col, date_col])

    # --- Optimized Revenue Logic ---
    df['Her Robux'] = 0.0
    
    # 1. Full Revenue Groups
    df.loc[df['Group Id'].isin(FULL_REVENUE_GROUPS), 'Her Robux'] = df[rev_col]
    
    # 2. 50% Groups
    df.loc[df['Group Id'].isin(FIFTY_PERCENT_GROUPS), 'Her Robux'] = df[rev_col] * 0.5
    
    # 3. Special Cape Group (The Filter Fix)
    cape_mask = (df['Group Id'] == SPECIAL_CAPE_GROUP) & (df[asset_col].astype(float).isin(ALLOWED_CAPE_ASSET_IDS))
    df.loc[cape_mask, 'Her Robux'] = df[rev_col] * 0.5

    # ====================== KPI SECTION ======================
    st.subheader("📅 Revenue Breakdown")
    now = pd.Timestamp.now("UTC")
    today = now.normalize()

    def calc_stats(df_slice):
        gross = int(df_slice[rev_col].sum())
        hers = int(df_slice['Her Robux'].sum())
        usd = hers * DEVEX_RATE
        return gross, hers, usd

    periods = {
        "Today": df[df[date_col] >= today],
        "Yesterday": df[(df[date_col] >= today - pd.Timedelta(days=1)) & (df[date_col] < today)],
        "Last 7 Days": df[df[date_col] >= today - pd.Timedelta(days=7)],
        "Last 28 Days": df[df[date_col] >= today - pd.Timedelta(days=28)],
        "All Time": df
    }

    cols = st.columns(len(periods))
    for i, (label, data) in enumerate(periods.items()):
        gross, hers, usd = calc_stats(data)
        with cols[i]:
            st.metric(label, f"R$ {hers:,}", f"Gross: {gross:,}")
            st.caption(f"**${usd:,.2f} USD**")

    # ====================== FILTERS ======================
    st.divider()
    preset = st.selectbox("Select Range for Charts", ["Last 7 days", "Last 28 days", "Last 90 days", "Custom"])

    if preset == "Custom":
        col1, col2 = st.columns(2)
        start_date = col1.date_input("Start", value=(now - pd.Timedelta(days=7)).date())
        end_date = col2.date_input("End", value=now.date())
    else:
        days = {"Last 7 days": 7, "Last 28 days": 28, "Last 90 days": 90}[preset]
        start_date, end_date = (now - pd.Timedelta(days=days)).date(), now.date()

    # Filter by Date
    mask = (df[date_col] >= pd.Timestamp(start_date).tz_localize("UTC")) & \
           (df[date_col] <= pd.Timestamp(end_date).tz_localize("UTC") + pd.Timedelta(days=1))
    filtered_df = df[mask].copy()

    # ====================== CHARTS ======================
    st.subheader("📈 Daily Trends (Gross vs. Her Share)")
    filtered_df['Date Only'] = filtered_df[date_col].dt.date
    daily = filtered_df.groupby('Date Only').agg({rev_col: 'sum', 'Her Robux': 'sum'}).reset_index()
    daily.columns = ['Date', 'Gross Robux', 'Her Robux']

    chart_data = daily.melt('Date', var_name='Type', value_name='Robux')
    line_chart = alt.Chart(chart_data).mark_line(point=True).encode(
        x='Date:T',
        y='Robux:Q',
        color='Type:N',
        tooltip=['Date', 'Type', 'Robux']
    ).properties(height=400)
    st.altair_chart(line_chart, use_container_width=True)

    # ====================== BEST SELLERS (CLEANED) ======================
    if name_col and asset_col:
        st.subheader("🏆 Top Items (Whitelisted Only)")
        
        # Aggregate
        top = filtered_df.groupby([name_col, asset_col]).agg({rev_col: 'sum', 'Her Robux': 'sum'}).reset_index()
        
        # FIX: Remove any items that have 0 Her Robux (hides non-whitelisted capes)
        top = top[top['Her Robux'] > 0]
        
        top = top.sort_values('Her Robux', ascending=False).head(25)
        
        if not top.empty:
            st.dataframe(
                top.style.format({rev_col: "{:,.0f}", "Her Robux": "{:,.0f}"}), 
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No sales found for whitelisted items in this period.")

    # ====================== DOWNLOAD ======================
    st.download_button("📥 Download Filtered CSV", filtered_df.to_csv(index=False), "roblox_split_data.csv")
