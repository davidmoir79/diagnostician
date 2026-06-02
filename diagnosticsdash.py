import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="Diagnostics Team Sample Dashboard", layout="wide")
st.title("Diagnostics Team Sample Dashboard")

DATA_FILE = Path("data.csv")
WORK_DAYS_PER_MONTH = 22
STATUS_ORDER = [0, 1, 2, 3, 4]
STATUS_COLORS = {0: "#2ca02c", 1: "#ffe28a", 2: "#ff9999", 3: "#8b0000", 4: "#800080"}

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

    # Try standard format first, fallback to mixed/flexible parsing if it fails
    df["date_time"] = pd.to_datetime(df["date_time"], format="%Y/%m/%d %H:%M", errors="coerce")
    fallback_mask = df["date_time"].isna()
    if fallback_mask.any():
        df.loc[fallback_mask, "date_time"] = pd.to_datetime(df.loc[fallback_mask, "date_time"], errors="coerce")

    df = df.dropna(subset=["date_time", "user"])
    df["user"] = df["user"].astype(str).str.strip()

    if "status" in df.columns:
        df["status_num"] = pd.to_numeric(
            df["status"].astype(str).str.extract(r"(\d+)", expand=False),
            errors="coerce",
        )
        df.loc[~df["status_num"].isin(STATUS_ORDER), "status_num"] = pd.NA
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
current_month_start = pd.Timestamp(latest_dt.year, latest_dt.month, 1)

# Set end_month to include the latest month found in your data instead of subtracting 1
end_month = current_month_start 

months_12 = pd.date_range(end=end_month, periods=12, freq="MS")
months_3 = pd.date_range(end=end_month, periods=3, freq="MS")

df_12 = df[df["date_time"].dt.to_period("M").dt.to_timestamp().isin(months_12)].copy()
df_12["month"] = df_12["date_time"].dt.to_period("M").dt.to_timestamp()

top_users = df_12["user"].value_counts().head(4).index.tolist()
df_top = df_12[df_12["user"].isin(top_users)].copy()

st.subheader("Top 4 diagnosticians")
st.write(", ".join(top_users))

st.caption(
    f"Reporting period: {months_12[0].strftime('%b %Y')} to {months_12[-1].strftime('%b %Y')} "
    f"(includes current/latest month)"
)

with st.sidebar:
    st.markdown("### Data Status Summary")
    st.write(f"**Total Valid Rows:** {len(df)}")
    st.write(f"**Max Date Detected:** {latest_dt}")

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
    category_orders={"label": month_order, "user": top_
