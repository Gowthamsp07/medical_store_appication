import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta


# ========================
# PAGE CONFIG
# ========================
st.set_page_config(
    page_title="Medical Store Dashboard",
    page_icon="💊",
    layout="wide"
)

# ========================
# CUSTOM CSS (White Futuristic Theme)
# ========================
st.markdown("""
    <style>
    .stApp { background: #ffffff; color: #000000; font-family: 'Poppins', sans-serif; }
    [data-testid="stSidebar"] { background: #f9f9f9; border-right: 2px solid #eee; }
    .dashboard-title { font-size: 38px; font-weight: 800; text-align: center;
                       background: linear-gradient(90deg, #007bff, #00e0ff);
                       -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                       margin-bottom: 10px; }
    .info-banner { background: rgba(255,255,255,0.7); border: 1px solid #e6e6e6;
                   border-radius: 20px; padding: 12px; font-size: 18px; text-align: center;
                   box-shadow: 0px 4px 20px rgba(0,0,0,0.05); margin-bottom: 25px; }
    .stat-card { background: rgba(255,255,255,0.6); border-radius: 25px; padding: 25px;
                 text-align: center; border: 1px solid rgba(200,200,200,0.3);
                 backdrop-filter: blur(12px); box-shadow: 0 6px 20px rgba(0,0,0,0.1);
                 transition: transform 0.3s ease-in-out, box-shadow 0.3s; }
    .stat-card:hover { transform: translateY(-6px); box-shadow: 0px 10px 30px rgba(0,123,255,0.2); }
    .stat-title { font-size: 18px; font-weight: 600; margin-bottom: 10px; color: #000000; }
    .stat-value { font-size: 36px; font-weight: bold; background: linear-gradient(90deg, #007bff, #00c6ff);
                  -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .alerts-title { font-size: 24px; font-weight: 700; margin-top: 30px; margin-bottom: 15px; color: #000000; }
    .alert-card { background: #fff5f5; border-left: 6px solid red; padding: 12px 18px; border-radius: 15px;
                  margin-bottom: 12px; font-size: 16px; color: black;
                  box-shadow: 0 3px 12px rgba(0,0,0,0.05); transition: transform 0.2s; }
    .alert-card:hover { transform: scale(1.02); box-shadow: 0px 8px 20px rgba(255,0,0,0.2); }
    .datetime-box { background: #ffffff; border: 1px solid #ddd; border-radius: 15px;
                    padding: 12px 20px; font-size: 16px; color: #000000; text-align: center;
                    box-shadow: 0px 4px 15px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

# ========================
# HEADER
# ========================
st.markdown('<h1 class="dashboard-title"> Medical Store Dashboard</h1>', unsafe_allow_html=True)
st.markdown('<div class="info-banner">✨ Welcome to your <b> Medical Store</b> 🚀 | Manage <b>Inventory, Billing, Alerts & Reports</b>  ✨</div>', unsafe_allow_html=True)

# ========================
# DATETIME
# ========================
col_time, _, _ = st.columns([1,2,1])
with col_time:
    now = datetime.now()
    st.markdown(f'<div class="datetime-box">📅 {now.strftime("%d %B %Y")}<br>⏰ {now.strftime("%I:%M %p")}</div>', unsafe_allow_html=True)

# ========================
# DATABASE FETCH
# ========================
conn = sqlite3.connect("medical_store.db", check_same_thread=False)
df = pd.read_sql("SELECT * FROM medicines", conn)

if df.empty:
    st.warning("⚠️ No medicines found in inventory.")
else:
    df["expiry_date"] = pd.to_datetime(df["expiry_date"], errors="coerce").dt.date

    # Stats
    total_stock = df["quantity"].sum()
    low_stock = df[df["quantity"] < 10].shape[0]
    expiring_soon = df[(df["expiry_date"] >= datetime.today().date()) &
                       (df["expiry_date"] <= datetime.today().date() + timedelta(days=30))].shape[0]

    # ========================
    # STATS CARDS
    # ========================
    st.subheader("📊 Current Overview")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="stat-card"><div class="stat-title">💊 Total Stock</div><div class="stat-value">{total_stock}</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stat-card"><div class="stat-title">⚠️ Low Stock Items</div><div class="stat-value">{low_stock}</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="stat-card"><div class="stat-title">⏳ Expiring Soon</div><div class="stat-value">{expiring_soon}</div></div>', unsafe_allow_html=True)

    # ========================
    # ALERTS (Dynamic)
    # ========================
    st.markdown('<div class="alerts-title">🔔 Important Alerts</div>', unsafe_allow_html=True)

    expired_df = df[df["expiry_date"] < datetime.today().date()]
    soon_df = df[(df["expiry_date"] >= datetime.today().date()) &
                 (df["expiry_date"] <= datetime.today().date() + timedelta(days=30))]

    if expired_df.empty and soon_df.empty:
        st.success("✅ No critical alerts right now.")
    else:
        for _, row in expired_df.iterrows():
            st.markdown(
                f'<div class="alert-card">❌ {row["name"]} (Batch: <b>{row["batch_no"]}</b>) → Expired on <b style="color:red;">{row["expiry_date"]}</b></div>',
                unsafe_allow_html=True
            )
        for _, row in soon_df.iterrows():
            st.markdown(
                f'<div class="alert-card">⏳ {row["name"]} (Batch: <b>{row["batch_no"]}</b>) → Expiry: <b style="color:red;">{row["expiry_date"]}</b></div>',
                unsafe_allow_html=True
            )
