Here is the complete, integrated script including the updated data filtering logic and the optimized, responsive layout.

Save this directly into your file (e.g., `app.py`) and run it via `streamlit run app.py`.

```python
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

# --- LINE GRAPH: TOP 4 VS. TOTAL PRODUCTION ---
month_order = [m.strftime("%b %Y") for m in months_12]

monthly_top_users = df_top.groupby(["month", "user"]).size().reset_index(name="samples")
monthly_top_users["label"] = monthly_top_users["month"].dt.strftime("%b %Y")

monthly_grand_total = df_12.groupby("month").size().reset_index(name="samples")
monthly_grand_total["user"] = "TOTAL (All Users)"
monthly_grand_total["label"] = monthly_grand_total["month"].dt.strftime("%b %Y")

combined_line_data = pd.concat([monthly_top_users, monthly_grand_total], ignore_index=True)
combined_line_data["label"] = pd.Categorical(combined_line_data["label"], categories=month_order, ordered=True)

legend_order = ["TOTAL (All Users)"] + top_users

fig1 = px.line(
    combined_line_data,
    x="label",
    y="samples",
    color="user",
    category_orders={"label": month_order, "user": legend_order},
    markers=True,
    title="Monthly samples: Top 4 vs. Grand Total (last 12 complete months)",
)

# Apply dynamic labels solely to the grand total trace line
fig1.update_traces(
    text=combined_line_data.loc[combined_line_data["user"] == "TOTAL (All Users)", "samples"],
    textposition="top center",
    mode="lines+markers+text",
    selector=dict(name="TOTAL (All Users)")
)
fig1.update_layout(xaxis_title="Month", yaxis_title="Samples", legend_title_text="User/Metric")
st.plotly_chart(fig1, use_container_width=True)


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
            .reset_index(name="count")
            .set_index("status_num")
            .reindex(STATUS_ORDER, fill_value=0)
            .reset_index()
        )

        with status_cols[i % 2]:
            if status_counts["count"].sum() == 0:
                st.caption(f"No valid status data for {user}.")
            else:
                fig = px.pie(
                    status_counts, names="status_num", values="count", hole=0.35,
                    title=f"{user} Status Mix", color="status_num", color_discrete_map=STATUS_COLORS,
                )
                fig.update_traces(textinfo="percent")
                fig.update_layout(showlegend=False if i % 2 == 1 else True, margin=dict(t=30, b=10, l=10, r=10))
                st.plotly_chart(fig, use_container_width=True)


# --- DATA SUMMARY MATRIX ---
st.markdown("---")
st.subheader("📋 Monthly Production Summary")
table_source = monthly_top_users.pivot_table(index="month", columns="user", values="samples", fill_value=0)
table = table_source.reindex(months_12, fill_value=0)
table.index = table.index.strftime("%b %Y")
st.dataframe(table, use_container_width=True)

```
