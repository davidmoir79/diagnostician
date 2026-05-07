import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="Diagnostics Team Sample Dashboard", layout="wide")
st.title("Diagnostics Team Sample Dashboard")

DATA_FILE = Path("data.csv")
WORK_DAYS_PER_MONTH = 22

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
    return df

if not DATA_FILE.exists():
    st.error("data.csv not found in the app folder. Add the CSV to the repo root.")
    st.stop()

df = load_data(DATA_FILE)

latest_dt = df["date_time"].max()
current_month = latest_dt.to_period("M").to_timestamp()
months_12 = pd.date_range(end=current_month, periods=12, freq="MS")

df_12 = df[df["date_time"].dt.to_period("M").dt.to_timestamp().isin(months_12)].copy()
df_12["month"] = df_12["date_time"].dt.to_period("M").dt.to_timestamp()

top_users = df_12["user"].value_counts().head(4).index.tolist()
df_top = df_12[df_12["user"].isin(top_users)].copy()

st.subheader("Top 4 diagnosticians")
st.write(", ".join(top_users))

monthly_user = df_top.groupby(["month", "user"]).size().reset_index(name="samples")
month_order = [m.strftime("%b %Y") for m in months_12]
monthly_user["label"] = monthly_user["month"].dt.strftime("%b %Y")
monthly_user["label"] = pd.Categorical(monthly_user["label"], categories=month_order, ordered=True)

fig1 = px.bar(
    monthly_user,
    x="label",
    y="samples",
    color="user",
    barmode="group",
    category_orders={"label": month_order, "user": top_users},
    text="samples",
    title="Monthly samples per top 4 diagnosticians (last 12 months)",
)
fig1.update_layout(xaxis_title="Month", yaxis_title="Samples")
st.plotly_chart(fig1, use_container_width=True)

user_month = df_top.groupby(["user", "month"]).size().reset_index(name="samples")
avg_month = user_month.groupby("user", as_index=False)["samples"].mean().rename(columns={"samples": "avg_samples_per_month"})
fig2 = px.bar(
    avg_month,
    x="user",
    y="avg_samples_per_month",
    text_auto=".2f",
    title="Average samples per month per diagnostician (last 12 months)",
)
fig2.update_layout(xaxis_title="User", yaxis_title="Avg samples/month")
st.plotly_chart(fig2, use_container_width=True)

avg_day = avg_month.copy()
avg_day["avg_samples_per_day"] = avg_day["avg_samples_per_month"] / WORK_DAYS_PER_MONTH
fig3 = px.bar(
    avg_day,
    x="user",
    y="avg_samples_per_day",
    text_auto=".2f",
    title="Average samples per day per diagnostician (22 work days/month)",
)
fig3.update_layout(xaxis_title="User", yaxis_title="Avg samples/day")
st.plotly_chart(fig3, use_container_width=True)

workload = df_top.groupby("user").size().reset_index(name="total_samples")
workload["percent_workload"] = 100 * workload["total_samples"] / workload["total_samples"].sum()
fig4 = px.pie(
    workload,
    names="user",
    values="total_samples",
    hole=0.35,
    title="Percent of total workload by diagnostician (last 12 months)",
)
st.plotly_chart(fig4, use_container_width=True)

st.subheader("Monthly table")
table = monthly_user.pivot_table(index="month", columns="user", values="samples", fill_value=0).reindex(months_12, fill_value=0)
table.index = table.index.strftime("%b %Y")
st.dataframe(table, use_container_width=True)
