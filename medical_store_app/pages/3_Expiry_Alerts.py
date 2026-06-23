import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

# ---------------- Page Config ----------------
st.set_page_config(page_title="Expiry Monitoring", page_icon="⏳", layout="wide")

# ---------------- Custom CSS ----------------
st.markdown("""
    <style>
        /* Background & text */
        body, .stApp {
            background-color: #ffffff;
            color: #000000;
            font-family: 'Segoe UI', sans-serif;
        }

        /* Title Styling */
        h1 {
            text-align: center;
            color: #066e91;
            font-size: 2.5rem !important;
            font-weight: 800 !important;
            margin-bottom: 1rem;
        }

        /* Subheaders */
        h3 {
            color: #333333;
            border-bottom: 3px solid #066e91;
            display: inline-block;
            padding-bottom: 5px;
            margin-top: 2rem;
        }

        /* Dataframes */
        .stDataFrame {
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
    </style>
""", unsafe_allow_html=True)

# ---------------- Title ----------------
st.title("⏳ Expiry Monitoring")

# ---------------- Database Connection ----------------
conn = sqlite3.connect("medical_store.db")
df = pd.read_sql("SELECT * FROM medicines", conn)

if df.empty:
    st.info("No medicines available in stock.")
else:
    today = datetime.today().date()
    df["expiry_date"] = pd.to_datetime(df["expiry_date"]).dt.date

    # Expired Medicines
    expired_df = df[df["expiry_date"] < today]

    # Expiring Soon (within 30 days)
    soon_df = df[(df["expiry_date"] >= today) &
                 (df["expiry_date"] <= today + timedelta(days=30))]

    # ---------------- Expired ----------------
    st.subheader("❌ Expired Medicines")
    if expired_df.empty:
        st.success("✅ No expired medicines.")
    else:
        st.error("⚠️ Expired Medicines Found!")
        st.dataframe(expired_df, use_container_width=True)

        # 🔔 Streamlit Toast Notifications
        for _, med in expired_df.iterrows():
            st.toast(f"⚠️ {med['name']} expired on {med['expiry_date']}!")

        # 🔔 System Notifications
        try:
            from plyer import notification
            for _, med in expired_df.iterrows():
                notification.notify(
                    title="Medicine Expired!",
                    message=f"{med['name']} expired on {med['expiry_date']}",
                    timeout=10
                )
        except Exception as e:
            st.warning("⚠️ System notifications not supported here.")

    # ---------------- Expiring Soon ----------------
    st.subheader("⏰ Medicines Expiring Soon (within 30 days)")
    if soon_df.empty:
        st.info("ℹ️ No medicines expiring in the next 30 days.")
    else:
        st.warning("⏰ These medicines are expiring soon!")
        st.dataframe(soon_df, use_container_width=True)

        # 🔔 Streamlit Toast Notifications
        for _, med in soon_df.iterrows():
            st.toast(f"⏰ {med['name']} expiring on {med['expiry_date']}!")

conn.close()
