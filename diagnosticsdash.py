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

top_users =
