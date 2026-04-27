import streamlit as st
import pandas as pd
import altair as alt

# --- Page Config ---
st.set_page_config(page_title="Roblox Analytics", layout="wide", page_icon="📊")
st.title("📊 Roblox Sales Dashboard - Her Revenue After Split")

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

        if hasattr(file, 'name'):
            name = file.name

            if '32600641' in name:
                temp_df['Group Id'] = 32600641
            elif '823805908' in name:
                temp_df['Group Id'] = 823805908
            elif '13860593' in name:
                temp_df['Group Id'] = 13860593
            elif '33024439' in name:
                temp_df['Group Id'] = 33024439
            elif '35387713' in name:
                temp_df['Group Id'] = 35387713

        df_list.append(temp_df)

    df = pd.concat(df_list, ignore_index=True)

    # ====================== DEDUPLICATION FIX ======================
    date_col = next((c for c in ['Date and Time', 'Created', 'Date'] if c in df.columns), None)
    rev_col = next((c for c in ['Revenue', 'Net Revenue', 'Amount', 'Robux Earned'] if c in df.columns), None)
    asset_col = next((c for c in ['Asset Id', 'Asset ID', 'AssetId'] if c in df.columns), None)
    name_col = next((c for c in ['Asset Name', 'Name'] if c in df.columns), None)

    dedupe_cols = [col for col in [date_col, rev_col, asset_col, name_col, 'Group Id'] if col]

    duplicates_removed = 0

    if dedupe_cols:
        before = len(df)
        df = df.drop_duplicates(subset=dedupe_cols, keep='first')
        after = len(df)
        duplicates_removed = before - after

    return df, duplicates_removed

# ====================== MAIN ======================
if uploaded_files:
    df, duplicates_removed = load_data(uploaded_files)

    if duplicates_removed > 0:
        st.warning(f"⚠️ Removed {duplicates_removed:,} duplicate rows")

    # --- Detect Columns ---
    date_col = next((c for c in ['Date and Time', 'Created', 'Date'] if c in df.columns), None)
    rev_col = next((c for c in ['Revenue', 'Net Revenue', 'Amount', 'Robux Earned'] if c in df.columns), None)
    asset_col = next((c for c in ['Asset Id', 'Asset ID', 'AssetId'] if c in df.columns), None)
    name_col = next((c for c in ['Asset Name', 'Name'] if c in df.columns), None)

    if not date_col or not rev_col:
        st.error("Missing required columns")
        st.stop()

    # --- Clean Data ---
    df[rev_col] = pd.to_numeric(
        df[rev_col].astype(str).str.replace(r"[^\d.-]", "", regex=True),
        errors='coerce'
    )
    df = df.dropna(subset=[rev_col])

    if asset_col:
        df[asset_col] = pd.to_numeric(df[asset_col], errors='coerce')

    df[date_col] = pd.to_datetime(df[date_col], utc=True, errors='coerce')
    df = df.dropna(subset=[date_col])

    now = pd.Timestamp.now("UTC")

    # ====================== SHARE LOGIC ======================
    def get_her_share(row):
        revenue = row[rev_col]
        group = int(row.get('Group Id', 0))
        asset_id = row.get(asset_col)

        if group == SPECIAL_CAPE_GROUP:
            if pd.notna(asset_id) and int(asset_id) in ALLOWED_CAPE_ASSET_IDS:
                return revenue * 0.5
            return 0

        if pd.notna(asset_id) and int(asset_id) in ALLOWED_CAPE_ASSET_IDS:
            return revenue * 0.5

        if group in FIFTY_PERCENT_GROUPS:
            return revenue * 0.5

        return revenue

    df['Her Robux'] = df.apply(get_her_share, axis=1)
    df['Her USD'] = df['Her Robux'] * DEVEX_RATE

    # ====================== GLOBAL KPIs ======================
    today = now.normalize()
    yesterday = today - pd.Timedelta(days=1)
    last_7 = today - pd.Timedelta(days=7)
    last_28 = today - pd.Timedelta(days=28)

    df_today = df[df[date_col] >= today]
    df_yesterday = df[(df[date_col] >= yesterday) & (df[date_col] < today)]
    df_7 = df[df[date_col] >= last_7]
    df_28 = df[df[date_col] >= last_28]

    def calc(df_slice):
        robux = int(df_slice['Her Robux'].sum())
        usd = robux * DEVEX_RATE
        return robux, usd

    t_r, t_u = calc(df_today)
    y_r, y_u = calc(df_yesterday)
    s_r, s_u = calc(df_7)
    l_r, l_u = calc(df_28)
    a_r, a_u = calc(df)

    st.subheader("📅 Revenue Breakdown")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Today", f"R$ {t_r:,}", f"${t_u:,.2f}")
    col2.metric("Yesterday", f"R$ {y_r:,}", f"${y_u:,.2f}")
    col3.metric("Last 7 Days", f"R$ {s_r:,}", f"${s_u:,.2f}")
    col4.metric("Last 28 Days", f"R$ {l_r:,}", f"${l_u:,.2f}")
    col5.metric("All Time", f"R$ {a_r:,}", f"${a_u:,.2f}")

    # ====================== DATE RANGE FILTER ======================
    st.divider()
    st.subheader("📅 Filter Data")

    preset = st.selectbox(
        "Select Range",
        ["Last 7 days", "Last 28 days", "Last 56 days", "Last 90 days", "Custom"]
    )

    if preset != "Custom":
        days_map = {
            "Last 7 days": 7,
            "Last 28 days": 28,
            "Last 56 days": 56,
            "Last 90 days": 90
        }
        start_date = (now - pd.Timedelta(days=days_map[preset])).date()
        end_date = now.date()
    else:
        col1, col2 = st.columns(2)
        start_date = col1.date_input("Start date", value=(now - pd.Timedelta(days=7)).date())
        end_date = col2.date_input("End date", value=now.date())

    start_dt = pd.to_datetime(start_date).tz_localize("UTC")
    end_dt = pd.to_datetime(end_date).tz_localize("UTC") + pd.Timedelta(days=1)

    filtered_df = df[(df[date_col] >= start_dt) & (df[date_col] < end_dt)]

    # ====================== DAILY GRAPH ======================
    st.divider()
    st.subheader("📈 Daily Sales Trend")

    filtered_df['Date Only'] = filtered_df[date_col].dt.date

    daily_sales = (
        filtered_df.groupby('Date Only')['Her Robux']
        .sum()
        .reset_index()
        .sort_values('Date Only')
    )

    daily_sales['Her USD'] = daily_sales['Her Robux'] * DEVEX_RATE

    metric_choice = st.radio("View:", ["Robux", "USD"], horizontal=True)

    y_axis = 'Her Robux' if metric_choice == "Robux" else 'Her USD'

    chart = alt.Chart(daily_sales).mark_line(
        interpolate='monotone',
        point=True
    ).encode(
        x=alt.X('Date Only:T', title="Date"),
        y=alt.Y(y_axis + ':Q', title=metric_choice),
        tooltip=['Date Only', y_axis]
    ).properties(height=400)

    st.altair_chart(chart, use_container_width=True)

    # ====================== BEST SELLERS ======================
    st.divider()
    st.subheader("🏆 Best Selling Items (Filtered)")

    if name_col and asset_col:
        top = (
            filtered_df.groupby([name_col, asset_col])['Her Robux']
            .sum()
            .reset_index()
            .sort_values('Her Robux', ascending=False)
        )

        top['Her USD'] = top['Her Robux'] * DEVEX_RATE

        st.dataframe(
            top.head(25).style.format({
                "Her Robux": "{:,.0f}",
                "Her USD": "${:,.2f}"
            }),
            use_container_width=True
        )

    # ====================== DOWNLOAD ======================
    st.download_button(
        "📥 Download Filtered Data",
        filtered_df.to_csv(index=False),
        file_name="roblox_filtered_revenue.csv"
    )
