import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="Diagnostics Team Sample Dashboard", layout="wide")
st.title("Diagnostics Team Sample Dashboard")

DATA_FILE = Path("data.csv")

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

    if "date_time" not in df.columns:
        raise ValueError(f"CSV columns found: {list(df.columns)}")
    if "user" not in df.columns:
        raise ValueError(f"CSV columns found: {list(df.columns)}")

    df["date_time"] = pd.to_datetime(df["date_time"], format="%Y/%m/%d %H:%M", errors="coerce")
    df = df.dropna(subset=["date_time", "user"])
    df["user"] = df["user"].astype(str).str.strip()

    if "status" in df.columns:
        df["status_num"] = df["status"].astype(str).str.extract(r"(\d+)", expand=False)
        df["status_num"] = pd.to_numeric(df["status_num"], errors="coerce")
    else:
        df["status_num"] = pd.NA

    return df

if not DATA_FILE.exists():
    st.error("data.csv not found in the app folder. Add the CSV to the repo root.")
    st.stop()

try:
    df = load_data(DATA_FILE)
except Exception as e:
    st.error(f"Failed to load CSV: {e}")
    st.stop()

latest_dt = df["date_time"].max()
current_month = latest_dt.to_period("M").to_timestamp()
months = pd.date_range(end=current_month, periods=24, freq="MS")

df_24 = df[df["date_time"].dt.to_period("M").dt.to_timestamp().isin(months)].copy()
df_24["month"] = df_24["date_time"].dt.to_period("M").to_timestamp()

monthly = df_24.groupby("month").size().reindex(months, fill_value=0).reset_index()
monthly.columns = ["month", "samples"]
monthly["label"] = monthly["month"].dt.strftime("%b %Y")

if len(months) >= 2:
    monthly.loc[monthly["month"] == months[-1], "label"] = "Last month"
    monthly.loc[monthly["month"] == months[-2], "label"] = "2 months ago"

user_month = df_24.groupby(["user", "month"]).size().reset_index(name="samples")
avg_user = (
    user_month.groupby("user", as_index=False)["samples"]
    .mean()
    .rename(columns={"samples": "avg_samples_per_month"})
    .sort_values("avg_samples_per_month", ascending=False)
)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Monthly samples")
    fig1 = px.bar(monthly, x="label", y="samples", text="samples")
    fig1.update_layout(xaxis_title="", yaxis_title="Samples")
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("Average samples per month by user")
    fig2 = px.bar(avg_user, x="user", y="avg_samples_per_month", text_auto=".2f")
    fig2.update_layout(xaxis_title="User", yaxis_title="Avg samples/month")
    st.plotly_chart(fig2, use_container_width=True)

st.subheader("Status percentage breakdown")
status_df = df_24.dropna(subset=["status_num"]).copy()

if status_df.empty:
    st.warning("No valid numeric status values found in the last 24 months.")
else:
    status_counts = status_df.groupby("status_num").size().reset_index(name="count")
    status_counts["percent"] = 100 * status_counts["count"] / status_counts["count"].sum()
    fig3 = px.pie(status_counts, names="status_num", values="count", hole=0.35)
    st.plotly_chart(fig3, use_container_width=True)

st.subheader("Data preview")
st.dataframe(df.head(100), use_container_width=True)
