import pandas as pd
from supabase import create_client
from datetime import timedelta
import os
from dotenv import load_dotenv

# ======================
# CONFIG
# ======================
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

SHEET_ID = "1DfUJd33T-12UVOavd6SqCfkcNl8_4sVxcqqXHtBeWpw"

YEAR_TABS = [
    "541668566",           # current year ONLY (important)
]

# ======================
# CONNECT
# ======================
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ======================
# GET LATEST DATE FROM DB
# ======================
response = (
    supabase.table("daily_health_metrics")
    .select("date")
    .order("date", desc=True)
    .limit(1)
    .execute()
)

latest_date = None

if response.data:
    latest_date = pd.to_datetime(response.data[0]["date"])
    print(f"Latest date in DB: {latest_date}")
else:
    print("No existing data found")

# Safety window (handles edits)
if latest_date is not None:
    cutoff_date = latest_date - timedelta(days=7)
else:
    cutoff_date = None

# ======================
# LOAD USERS
# ======================
users = supabase.table("users").select("*").execute()
users_df = pd.DataFrame(users.data)
user_map = dict(zip(users_df["name"], users_df["user_id"]))

# ======================
# PROCESS
# ======================
BATCH_SIZE = 500

for gid in YEAR_TABS:

    print(f"Processing tab {gid}")

    csv_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    df = pd.read_csv(csv_url)

    df_long = df.melt(id_vars=["User"], var_name="date", value_name="steps")

    df_long["date"] = pd.to_datetime(df_long["date"], format="%d-%b-%Y", errors="coerce")
    df_long["steps"] = pd.to_numeric(df_long["steps"], errors="coerce").fillna(0)

    df_long = df_long.dropna(subset=["date"])

    # 🔥 FILTER ONLY NEW / RECENT DATA
    if cutoff_date is not None:
        df_long = df_long[df_long["date"] >= cutoff_date]

    df_long["user_id"] = df_long["User"].map(user_map)
    df_long = df_long.dropna(subset=["user_id"])

    df_long["metric"] = "steps"
    df_long["source"] = "google_sheet_incremental"
    df_long["device"] = "unknown"

    records = df_long[[
        "user_id",
        "date",
        "metric",
        "steps",
        "source",
        "device"
    ]].rename(columns={"steps": "value"}).to_dict("records")

    print(f"Uploading {len(records)} rows...")

    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i:i+BATCH_SIZE]
        supabase.table("daily_health_metrics").upsert(
            batch,
            on_conflict="user_id,date,metric"
        ).execute()

print("✅ Incremental sync complete")
