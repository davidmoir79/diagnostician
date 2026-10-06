import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Diagnostics Team Sample Dashboard", layout="wide")
st.title("📊 Diagnostics Team Sample Dashboard")

DATA_FILE = Path("data.csv")
WORK_DAYS_PER_MONTH = 22
STATUS_ORDER = [0, 1, 2, 3, 4]
STATUS_COLORS = {0: "#2ca02c", 1: "#ffe28a", 2: "#ff9999", 3: "#8b0000", 4: "#800080"}

# --- DATA LOADING & CLEANING ---
@st.cache_data
def load_data(path):
    df = pd.read_csv(path, sep=";")
    df.columns = df.columns.astype(str).str.strip().str.lower().str.replace(" ", "_")
    
    rename_map = {
        "datetime": "date_time",
        "date": "date_time",
        "date-time": "date_time",
        "sample_date": "date_time",
    }
    df = df.rename(columns=rename_map)

    if "date_time" not in df.columns or "user" not in df.columns:
        raise ValueError(f"Required columns missing. Found: {list(df.columns)}")

    # Parse dates with robust fallback
    df["date_time"] = pd.to_datetime(df["date_time"], format="%Y/%m/%d %H:%M", errors="coerce")
    fallback_mask = df["date_time"].isna()
    if fallback_mask.any():
        df.loc[fallback_mask, "date_time"] = pd.to_datetime(df.loc[fallback_mask, "date_time"], errors="coerce")

    # Drop rows missing core identification info
    df = df.dropna(subset=["date_time", "user"])
    df["user"] = df["user"].astype(str).str.strip()

    # --- FILTER AND IGNORE NON-NUMERIC/INVALID STATUSES ---
    if "status" in df.columns:
        # Extract numeric values; string/non-numeric values automatically become NaN
        df["status_num"] = pd.to_numeric(
            df["status"].astype(str).str.extract(r"(\d+)", expand=False),
            errors="coerce",
        )
        # Enforce that numbers must be within the valid status list (0-4)
        df.loc[~df["status_num"].isin(STATUS_ORDER), "status_num"] = pd.NA
        
        # Completely drop rows where the status is missing, text-only, or invalid
        df = df.dropna(subset=["status_num"])
        df["status_num"] = df["status_num"].astype(int)
    else:
        raise ValueError("The provided CSV file is missing the required 'status' column.")

    return df

# --- INITIAL CHECKS ---
if not DATA_FILE.exists():
    st.error("🚨 data.csv not found in the app folder. Add the CSV to the repo root.")
    st.stop()

try:
    df = load_data(DATA_FILE)
except Exception as e:
    st.error(f"🚨 Failed to load CSV: {e}")
    st.stop()

# --- TIME RANGE SETUP ---
latest_dt = df["date_time"].max()
current_month_start = pd.Timestamp(latest_dt.year, latest_dt.month, 1)
end_month = current_month_start 

months_12 = pd.date_range(end=end_month, periods=12, freq="MS")
months_3 = pd.date_range(end=end_month, periods=3, freq="MS")

df_12 = df[df["date_time"].dt.to_period("M").dt.to_timestamp().isin(months_12)].copy()
df_12["month"] = df_12["date_time"].dt.to_period("M").dt.to_timestamp()

top_users = df_12["user"].value_counts().head(4).index.tolist()
df_top = df_12[df_12["user"].isin(top_users)].copy()

# --- SIDEBAR STATISTICS ---
with st.sidebar:
    st.markdown("### 🗃️ Data Status Summary")
    st.metric(label="Total Clean Rows", value=f"{len(df):,}")
    st.write(f"**Max Date Detected:** {latest_dt.strftime('%Y-%m-%d %H:%M')}")
    st.caption(
        f"Reporting period: {months_12[0].strftime('%b %Y')} to {months_12[-1].strftime('%b %Y')} "
        f"(includes current/latest month)"
    )

st.subheader("👥 Top 4 Diagnosticians")
st.markdown(", ".join([f"**{user}**" for user in top_users]))

# --- LINE GRAPH: GRAND TOTAL ONLY ---
month_order = [m.strftime("%b %Y") for m in months_12]

monthly_grand_total = df_12.groupby("month").size().reset_index(name="samples")
monthly_grand_total["label"] = monthly_grand_total["month"].dt.strftime("%b %Y")
monthly_grand_total["label"] = pd.Categorical(monthly_grand_total["label"], categories=month_order, ordered=True)

fig_total = px.line(
    monthly_grand_total,
    x="label",
    y="samples",
    markers=True,
    title="Monthly samples: Grand Total (last 12 complete months)",
)
fig_total.update_traces(
    text=monthly_grand_total["samples"],
    textposition="top center",
    mode="lines+markers+text",
)
fig_total.update_layout(xaxis_title="Month", yaxis_title="Samples", showlegend=False)
st.plotly_chart(fig_total, use_container_width=True)

# --- LINE GRAPH: ALL 4 DIAGNOSTICIANS TOGETHER ---
st.subheader("📈 Diagnostician Trends (Last 12 Months)")

monthly_top_users = df_top.groupby(["month", "user"]).size().reset_index(name="samples")
monthly_top_users["label"] = monthly_top_users["month"].dt.strftime("%b %Y")
monthly_top_users["label"] = pd.Categorical(monthly_top_users["label"], categories=month_order, ordered=True)

legend_order = top_users  # ensures consistent order

fig_users = px.line(
    monthly_top_users,
    x="label",
    y="samples",
    color="user",
    category_orders={"user": legend_order},
    markers=True,
    title="Monthly samples: Top 4 Diagnosticians",
)
fig_users.update_layout(
    xaxis_title="Month",
    yaxis_title="Samples",
    legend_title_text="Diagnostician",
)
st.plotly_chart(fig_users, use_container_width=True)

# --- DUAL-COLUMN TIME ANALYSIS METRICS ---
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🗓️ Last 12 Months Analysis")
    user_month = df_top.groupby(["user", "month"]).size().reset_index(name="samples")
    avg_month = user_month.groupby("user", as_index=False)["samples"].mean().rename(columns={"samples": "avg_samples_per_month"})
    
    fig2 = px.bar(
        avg_month, x="user", y="avg_samples_per_month", text_auto=".2f",
        title="Avg samples per month per diagnostician",
    )
    fig2.update_layout(xaxis_title="User", yaxis_title="Avg samples/month")
    st.plotly_chart(fig2, use_container_width=True)

    avg_day = avg_month.copy()
    avg_day["avg_samples_per_day"] = avg_day["avg_samples_per_month"] / WORK_DAYS_PER_MONTH
    fig3 = px.bar(
        avg_day, x="user", y="avg_samples_per_day", text_auto=".2f",
        title="Avg samples per day per diagnostician (22 work days/month)",
    )
    fig3.update_layout(xaxis_title="User", yaxis_title="Avg samples/day")
    st.plotly_chart(fig3, use_container_width=True)

with col2:
    st.markdown("### ⏱️ Last 3 Months Analysis")
    last3 = df_top[df_top["month"].isin(months_3)].copy()
    last3_user_month = last3.groupby(["user", "month"]).size().reset_index(name="samples")
    last3_avg = last3_user_month.groupby("user", as_index=False)["samples"].mean().rename(columns={"samples": "avg_samples_per_month"})
    last3_avg = last3_avg.set_index("user").reindex(top_users).reset_index()

    fig2b = px.bar(
        last3_avg, x="user", y="avg_samples_per_month", text_auto=".2f",
        title="Avg samples per month per diagnostician",
    )
    fig2b.update_layout(xaxis_title="User", yaxis_title="Avg samples/month")
    st.plotly_chart(fig2b, use_container_width=True)

    avg_day_3 = last3_avg.copy()
    avg_day_3["avg_samples_per_day"] = avg_day_3["avg_samples_per_month"] / WORK_DAYS_PER_MONTH
    fig3b = px.bar(
        avg_day_3, x="user", y="avg_samples_per_day", text_auto=".2f",
        title="Avg samples per day per diagnostician (22 work days/month)",
    )
    fig3b.update_layout(xaxis_title="User", yaxis_title="Avg samples/day")
    st.plotly_chart(fig3b, use_container_width=True)


# --- DISTRIBUTION PANELS ---
st.markdown("---")
col_pie1, col_pie2 = st.columns([1, 2])

with col_pie1:
    st.markdown("### 📊 Workload Share")
    workload = df_top.groupby("user").size().reset_index(name="total_samples")
    fig4 = px.pie(
        workload, names="user", values="total_samples", hole=0.35,
        title="Total workload by diagnostician (Last 12 Mo.)",
    )
    st.plotly_chart(fig4, use_container_width=True)

with col_pie2:
    st.markdown("### 🏷️ Status Selection Breakdown")
    status_cols = st.columns(2)
    for i, user in enumerate(top_users):
        user_status = df_top[df_top["user"] == user].copy()
        status_counts = (
            user_status.groupby("status_num").size()
