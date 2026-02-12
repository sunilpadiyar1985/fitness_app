import pandas as pd
import requests
from supabase import create_client
from datetime import datetime
import os
from dotenv import load_dotenv

# ======================
# CONFIG
# ======================

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Google Sheet CSV export link
SHEET_ID = "1DfUJd33T-12UVOavd6SqCfkcNl8_4sVxcqqXHtBeWpw"

# List all yearly tabs here (gid values)
YEAR_TABS = [
    "1074409226",  # 2024
    "0",           # 2025
    "541668566",   # 2026
]

# ======================
# CONNECT SUPABASE
# ======================

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ======================
# LOAD USERS TABLE
# ======================

users_response = supabase.table("users").select("*").execute()
users_df = pd.DataFrame(users_response.data)

user_map = dict(zip(users_df["name"], users_df["user_id"]))

print(f"Loaded {len(user_map)} users from Supabase")

# ======================
# PROCESS SHEETS
# ======================

all_rows = []

for gid in YEAR_TABS:
    print(f"Processing tab {gid}")

    csv_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    df = pd.read_csv(csv_url)

    # Melt wide -> long
    df_long = df.melt(id_vars=["User"], var_name="date", value_name="steps")

    # Clean
    df_long["date"] = pd.to_datetime(df_long["date"], format="%d-%b-%Y", errors="coerce")
    df_long["steps"] = pd.to_numeric(df_long["steps"], errors="coerce").fillna(0)

    df_long = df_long.dropna(subset=["date"])

    # Map user_id
    df_long["user_id"] = df_long["User"].map(user_map)

    df_long = df_long.dropna(subset=["user_id"])

    df_long["metric"] = "steps"
    df_long["source"] = "google_sheet_backfill"
    df_long["device"] = "unknown"

    records = df_long[[
        "user_id",
        "date",
        "metric",
        "steps",
        "source",
        "device"
    ]].rename(columns={"steps": "value"})

    all_rows.extend(records.to_dict("records"))

print(f"Prepared {len(all_rows)} rows for upload")

# ======================
# PUSH TO SUPABASE
# ======================

BATCH_SIZE = 500

for i in range(0, len(all_rows), BATCH_SIZE):
    batch = all_rows[i:i+BATCH_SIZE]
    supabase.table("daily_health_metrics").upsert(batch).execute()
    print(f"Uploaded {i + len(batch)} rows")

print("Migration complete 🚀")
