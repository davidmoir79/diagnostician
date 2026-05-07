import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import re

st.set_page_config(page_title="Diagnostics Monthly Samples", layout="wide")

st.title("Diagnostics Team Sample Dashboard")

uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

@st.cache_data
def load_data(file):
    df = pd.read_csv(file)
    df["date_time"] = pd.to_datetime(df["date_time"], errors="coerce")
    df = df.dropna(subset=["date_time", "user"])
    if "status" in df.columns:
        df["status_number"] = (
            df["status"]
            .astype(str)
            .str.extract(r"(\d+)", expand=False)
            .astype(float)
        )
    else:
        df["status_number"] = pd.NA
    return df

def month_label(dt):
    return dt.strftime("%Y-%m")

if uploaded_file:
    df = load_data(uploaded_file)

    df["month"] = df["date_time"].dt.to_period("M").dt.to_timestamp()

    latest_month = df["month"].max()
    last_24_months = pd.date_range(end=latest_month, periods=24, freq="MS")
    df_24 = df[df["month"].isin(last_24_months)].copy()

    month_map = {last_24_months[-1]: "Last month"}
    month_map[last_24_months[-2]] = "2 months ago"

    # Monthly samples overall
    monthly = (
        df_24.groupby("month")
        .size()
        .reindex(last_24_months, fill_value=0)
        .reset_index(name="samples")
    )
    monthly["display_month"] = monthly["month"].map(month_map).fillna(monthly["month"].dt.strftime("%b %Y"))

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Monthly samples")
        fig_month = px.bar(
            monthly,
            x="display_month",
            y="samples",
            title="Samples by month",
            text="samples",
        )
        fig_month.update_layout(xaxis_title="", yaxis_title="Samples")
        st.plotly_chart(fig_month, use_container_width=True)

    with col2:
        st.subheader("Average samples per month by user")
        user_month = (
            df_24.groupby(["user", "month"])
            .size()
            .reset_index(name="samples")
        )
        avg_user = (
            user_month.groupby("user")["samples"]
            .mean()
            .reset_index(name="avg_samples_per_month")
            .sort_values("avg_samples_per_month", ascending=False)
        )
        fig_user = px.bar(
            avg_user,
            x="user",
            y="avg_samples_per_month",
            title="Average samples per month per user (last 24 months)",
            text_auto=".2f",
        )
        fig_user.update_layout(xaxis_title="User", yaxis_title="Avg samples/month")
        st.plotly_chart(fig_user, use_container_width=True)

    st.subheader("Status percentage breakdown")
    status_data = df_24.dropna(subset=["status_number"]).copy()
    status_counts = (
        status_data.groupby("status_number")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    status_counts["percent"] = 100 * status_counts["count"] / status_counts["count"].sum()

    fig_pie = px.pie(
        status_counts,
        names="status_number",
        values="count",
        title="Status distribution for last 24 months",
        hole=0.35,
    )
    st.plotly_chart(fig_pie, use_container_width=True)

    st.subheader("Data preview")
    st.dataframe(df.head(50), use_container_width=True)
else:
    st.info("Upload a CSV file to begin.")
