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

st.set_page_config(page_title="Roblox Pro Analytics", layout="wide")
st.title("🚀 Roblox Sales & Catalog Dashboard")

# Sidebar
group_id = st.sidebar.text_input("Enter Roblox Group ID", value="823805908")
uploaded_file = st.file_uploader("Upload 'Sale of Goods' CSV", type=["csv"])

# --- NEW: UNLIMITED ITEM SCANNER ---
def get_all_group_items(gid):
    all_items = []
    cursor = ""
    # Categories: 3=Clothing, 11=Accessories, 12=Animations
    for cat in [3, 11, 12]:
        cursor = ""
        while True:
            url = f"https://catalog.roblox.com/v1/search/items/details?Category={cat}&CreatorTargetId={gid}&CreatorType=2&Limit=30&Cursor={cursor}"
            try:
                r = requests.get(url)
                if r.status_code == 200:
                    data = r.json()
                    all_items.extend(data.get('data', []))
                    cursor = data.get('nextPageCursor')
                    if not cursor: break # No more pages
                else: break
            except: break
    return all_items

if group_id:
    with st.sidebar:
        with st.spinner("Scanning Catalog..."):
            items = get_all_group_items(group_id)
            st.success(f"📦 Total Items Found: {len(items)}")
            if len(items) > 0:
                st.write("---")
                st.caption("Top Items Live:")
                for item in items[:5]:
                    st.write(f"🔹 {item['name']}")

# --- CSV PROCESSING (Earnings) ---
if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        df.columns = [c.strip() for c in df.columns]

        date_col = next((c for c in ['Date and Time', 'Sale Date and Time', 'Created'] if c in df.columns), None)
        rev_col = next((c for c in ['Revenue', 'Net Revenue'] if c in df.columns), None)
        item_col = next((c for c in ['Asset Name', 'Item'] if c in df.columns), None)

        if date_col and rev_col:
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            df = df.dropna(subset=[date_col])
            now = datetime.now(df[date_col].dt.tz)
            
            st.subheader("💰 Revenue Summary")
            c1, c2, c3 = st.columns(3)
            c1.metric("24 Hours", f"R$ {int(df[df[date_col] >= (now - timedelta(days=1))][rev_col].sum()):,}")
            c2.metric("7 Days", f"R$ {int(df[df[date_col] >= (now - timedelta(days=7))][rev_col].sum()):,}")
            c3.metric("30 Days", f"R$ {int(df[df[date_col] >= (now - timedelta(days=30))][rev_col].sum()):,}")

            st.divider()
            st.subheader("📈 30-Day Trend")
            chart_data = df[df[date_col] >= (now - timedelta(days=30))].copy()
            chart_data['Day'] = chart_data[date_col].dt.date
            st.line_chart(chart_data.groupby('Day')[rev_col].sum())
    except Exception as e:
        st.error(f"Error: {e}")
