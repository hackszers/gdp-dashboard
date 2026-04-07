import streamlit as st
import pandas as pd

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

    return pd.concat(df_list, ignore_index=True)

# ====================== MAIN ======================
if uploaded_files:
    df = load_data(uploaded_files)

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

    # ====================== TIME FILTERS ======================
    today = now.normalize()
    yesterday = today - pd.Timedelta(days=1)
    last_28 = today - pd.Timedelta(days=28)

    df_today = df[df[date_col] >= today]
    df_yesterday = df[(df[date_col] >= yesterday) & (df[date_col] < today)]
    df_28 = df[df[date_col] >= last_28]

    # ====================== KPI FUNCTION ======================
    def calc(df_slice):
        robux = int(df_slice['Her Robux'].sum())
        usd = robux * DEVEX_RATE
        return robux, usd

    t_r, t_u = calc(df_today)
    y_r, y_u = calc(df_yesterday)
    l_r, l_u = calc(df_28)
    a_r, a_u = calc(df)

    # ====================== KPI DISPLAY ======================
    st.subheader("📅 Revenue Breakdown")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Today", f"R$ {t_r:,}", f"${t_u:,.2f}")
    col2.metric("Yesterday", f"R$ {y_r:,}", f"${y_u:,.2f}")
    col3.metric("Last 28 Days", f"R$ {l_r:,}", f"${l_u:,.2f}")
    col4.metric("All Time", f"R$ {a_r:,}", f"${a_u:,.2f}")

    # ====================== BEST SELLERS ======================
    st.divider()
    st.subheader("🏆 Best Selling Items (Her Revenue)")

    if name_col and asset_col:
        top = (
            df.groupby([name_col, asset_col])['Her Robux']
            .sum()
            .reset_index()
            .sort_values('Her Robux', ascending=False)
        )

        top['Her USD'] = top['Her Robux'] * DEVEX_RATE

        st.dataframe(
            top.head(25).style.format({
                "Her Robux": "{:,.0f}",
                "Her USD": "${:,.2f}"
            })
        )

    # ====================== DOWNLOAD ======================
    st.download_button(
        "📥 Download Full Data",
        df.to_csv(index=False),
        file_name="roblox_revenue.csv"
    )
