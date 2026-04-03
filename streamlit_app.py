import os, subprocess, sys
import streamlit as st

# --- AUTO-INSTALLER ---
def install(package):
    try: subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    except: pass

try:
    import pandas as pd
    import requests
    import plotly.express as px # Added for complex charting
except ImportError:
    install('pandas')
    install('requests')
    install('plotly')
    import pandas as pd
    import requests
    import plotly.express as px

from datetime import datetime, timedelta

# --- Page Config ---
st.set_page_config(page_title="Roblox Analytics", layout="wide", page_icon="📊")
st.title("📊 Roblox Sales Dashboard")

# --- Sidebar ---
group_id = st.sidebar.text_input("Enter Roblox Group ID", value="823805908")

st.sidebar.divider()
st.sidebar.subheader("DevEx Settings")
# Standard DevEx rate is $0.0035 per 1 Robux
devex_rate = st.sidebar.number_input("Exchange Rate (USD/1 R$)", value=0.0035, format="%.4f")

uploaded_file = st.file_uploader("Upload 'Sale of Goods' CSV", type=["csv"])

if uploaded_file is not None:
    try:
        # Load and clean CSV
        df = pd.read_csv(uploaded_file)
        df.columns = [c.strip() for c in df.columns]

        # Standardizing column names for flexible parsing
        date_col = 'Date and Time' if 'Date and Time' in df.columns else 'Created'
        rev_col = 'Revenue' if 'Revenue' in df.columns else 'Net Revenue'
        item_col = 'Asset Name' if 'Asset Name' in df.columns else 'Item'

        if date_col in df.columns and rev_col in df.columns:
            # Handle timestamps (with potential timezones from Roblox CSVs)
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            df = df.dropna(subset=[date_col])
            
            # Use data's timezone for calculations, or default to current date
            if df[date_col].dt.tz:
                now = datetime.now(df[date_col].dt.tz)
            else:
                now = datetime.now()

            today_date = now.date()
            yesterday_date = today_date - timedelta(days=1)
            
            # Create dataframes for specific time windows
            df_today = df[df[date_col].dt.date == today_date]
            df_yesterday = df[df[date_col].dt.date == yesterday_date]
            df_7d = df[df[date_col] >= (now - timedelta(days=7))]
            # We filter for a full 31-day window to mirror the new graph
            df_31d = df[df[date_col] >= (now - timedelta(days=31))]

            # --- TOP METRICS WITH DEVEX ---
            st.subheader("💰 Revenue Summary")
            c1, c2, c3, c4 = st.columns(4)
            
            periods = [
                ("Today", df_today),
                ("Yesterday", df_yesterday),
                ("Past 7 Days", df_7d),
                ("Past 31 Days", df_31d)
            ]
            
            # Reuse columns 1 through 4
            cols = [c1, c2, c3, c4]
            
            # Loop through periods to populate metrics
            for i, (label, data) in enumerate(periods):
                robux_sum = int(data[rev_col].sum())
                # Perform DevEx calculation
                usd_val = robux_sum * devex_rate
                cols[i].metric(label, f"R$ {robux_sum:,}")
                # We use .write() so the USD amount sits clearly beneath the Robux metric
                cols[i].write(f"**Est. USD:** ${usd_val:,.2f}")

            # --- THE NEW MULTI-LINE GRAPH (Matching Reference) ---
            st.divider()
            st.subheader("📈 Past 31 Days Trend (By Asset)")

            # Step 1: Find your Top 5 highest revenue items in this period
            top_asset_names = (
                df_31d.groupby(item_col)[rev_col]
                .sum()
                .sort_values(ascending=False)
                .head(5)
                .index.tolist()
            )

            # Step 2: Create a daily summary dataframe (Date | Asset Name | Daily Revenue)
            # This 'chart_raw' dataframe is formatted correctly for multi-line plotting
            chart_raw = df_31d.copy()
            chart_raw['Date'] = chart_raw[date_col].dt.date
            
            # Group by both Date and Item to get specific sales
            daily_chart_items = (
                chart_raw.groupby(['Date', item_col])[rev_col]
                .sum()
                .reset_index()
            )

            # Step 3: Identify sales that are NOT in the Top 5 to group them as "Other"
            daily_chart_items['Chart Category'] = daily_chart_items[item_col].where(
                daily_chart_items[item_col].isin(top_asset_names), 
                'Other Assets'
            )

            # Step 4: Final daily aggregation. 
            # We must group again by 'Chart Category' to handle "Other Assets"
            final_daily_chart_data = (
                daily_chart_items.groupby(['Date', 'Chart Category'])[rev_col]
                .sum()
                .reset_index()
            )

            # Step 5: Add the "Total" line (must sum all revenue for that date)
            # The 'Total' line will use all assets, not just Top 5 or Other.
            total_revenue_daily = (
                chart_raw.groupby('Date')[rev_col]
                .sum()
                .reset_index()
            )
            total_revenue_daily['Chart Category'] = 'Total Revenue'

            # Step 6: Combine everything into one final DataFrame
            plot_df = pd.concat([final_daily_chart_data, total_revenue_daily], ignore_index=True)

            # Step 7: Render the plot using Plotly Express
            # Using Plotly allows us to match the styling and interactive legend of the reference.
            if not plot_df.empty:
                fig = px.line(
                    plot_df, 
                    x='Date', 
                    y=rev_col, 
                    color='Chart Category', 
                    title='', # Let the st.subheader handle the title
                    markers=True, # Shows data points (matches the small dots in your photo)
                    render_mode='svg' # Faster rendering
                )
                
                # Plotly Styling Adjustments to match the reference look:
                # 1. Place the legend *below* the chart
                # 2. Make the y-axis show labels (K, M) and start at zero
                fig.update_layout(
                    legend=dict(
                        orientation="h",
                        yanchor="top",
                        y=-0.3, # Push legend down
                        xanchor="center",
                        x=0.5,
                        title_text='' # Remove "Chart Category" title from legend
                    ),
                    yaxis_title='Revenue (R$)',
                    xaxis_title='', # Let the date range clarify the x-axis
                    yaxis=dict(rangemode="tozero") # Start y-axis at 0 R$
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No sales data available to chart in the last 31 days.")

            # --- TOP ITEMS TABLE ---
            st.divider()
            st.subheader("🏆 Top Selling Assets (Last 31 Days)")
            top_items = df_31d.groupby(item_col).agg({
                rev_col: 'sum',
                item_col: 'count'
            }).rename(columns={item_col: 'Sales', rev_col: 'Total Robux'})
            
            top_items['Total Robux'] = top_items['Total Robux'].astype(int)
            # Add Est. USD column to the table as well
            top_items['Est. USD'] = (top_items['Total Robux'] * devex_rate).round(2)
            top_items = top_items.sort_values(by='Total Robux', ascending=False)
            
            st.table(top_items.head(15).style.format({
                "Sales": "{:,}",
                "Total Robux": "{:,}",
                "Est. USD": "${:,.2f}"
            }))
            
    except Exception as e:
        # Graceful error handling in case of an issue with the CSV formatting.
        st.error(f"Error processing CSV: {e}")

# Sidebar Info (Kept from original script)
if group_id:
    try:
        r = requests.get(f"https://catalog.roblox.com/v1/search/items/details?Category=3&CreatorTargetId={group_id}&CreatorType=2")
        if r.status_code == 200:
            count = len(r.json().get('data', []))
            st.sidebar.success(f"📦 Recent Items: {count}")
    except: pass
