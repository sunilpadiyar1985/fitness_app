import streamlit as st
import pandas as pd
import os
from supabase import create_client
from dotenv import load_dotenv

# load env variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# connect
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("Fitness Dashboard v2")

# fetch data
response = supabase.table("daily_health_metrics").select("*").execute()

data = response.data

df = pd.DataFrame(data)

st.subheader("Raw health data from Supabase")
st.write(df)
