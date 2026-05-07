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
        df["status_num"] = pd.to_numeric(
            df["status"].astype(str).str.extract(r"(\d+)", expand=False),
            errors="coerce",
        )
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
months_12 = pd.date_range(end=current_month, periods=12, freq="MS")

df_12 = df[df["date_time"].dt.to_period("M").dt.to_timestamp().isin(months_12)].copy()
df_12["month"] = df_12["date_time"].dt.to_period("M").dt.to_timestamp()

top_users = df_12["user"].value_counts().head(4).index.tolist()
df_top = df_12[df_12["user"].isin(top_users)].copy()

st.subheader("Top 4 diagnosticians")
st.write(", ".join(top_users))

monthly_user = df_top.groupby(["month", "user"]).size().reset_index(name="samples")
monthly_user["label"] = monthly_user["month"].dt.strftime("%b %Y")
month_order = [m.strftime("%b %Y") for m in months_12]
monthly_user["label"] = pd.Categorical(monthly_user["label"], categories=month_order, ordered=True)

fig = px.bar(
    monthly_user,
    x="label",
    y="samples",
    color="user",
    barmode="group",
    category_orders={"label": month_order, "user": top_users},
    text="samples",
    title="Monthly samples per top 4 diagnosticians (last 12 months)",
)
fig.update_layout(xaxis_title="Month", yaxis_title="Samples")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Monthly table")
table = monthly_user.pivot_table(
    index="label",
    columns="user",
    values="samples",
    fill_value=0,
).reindex(month_order)

st.dataframe(table, use_container_width=True)
