import streamlit as st
import sqlite3
import pandas as pd

# ------------------- Page Config -------------------
st.set_page_config(
    page_title="Stock Reports",
    page_icon="📊",
    layout="wide"
)

# ------------------- Custom CSS -------------------
st.markdown("""
    <style>
        /* White background and clean fonts */
        .stApp {
            background-color: #ffffff;
            font-family: 'Segoe UI', sans-serif;
            color: #1f2937;
        }
        h1 {
            text-align: center;
            color: #0e7490 !important;
            font-weight: 900;
            font-size: 36px;
            margin-bottom: 30px;
        }
        h2 {
            color: #0e7490 !important;
            font-weight: 700;
            margin-top: 25px;
            margin-bottom: 15px;
        }
        .card {
            background: #f0f9ff;
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            font-weight: bold;
            font-size: 18px;
            color: #0e7490;
            box-shadow: 0px 5px 15px rgba(0,0,0,0.05);
            margin-bottom: 20px;
        }
        .dataframe th {
            background-color: #0e7490 !important;
            color: white !important;
            text-align: center !important;
        }
        .dataframe td {
            text-align: center !important;
            padding: 6px;
            font-size: 14px;
        }
        .low-stock {
            background-color: #fee2e2 !important;
        }
    </style>
""", unsafe_allow_html=True)

# ------------------- Title -------------------
st.markdown("<h1>📊 Futuristic Stock Reports</h1>", unsafe_allow_html=True)

# ------------------- Database Connection -------------------
conn = sqlite3.connect("medical_store.db")
df = pd.read_sql("SELECT * FROM medicines", conn)

# ------------------- Summary Cards -------------------
total_meds = len(df)
total_quantity = df["quantity"].sum()
low_stock_count = len(df[df["quantity"] < 10])

col1, col2, col3 = st.columns(3)
col1.markdown(f"<div class='card'>💊 Total Medicines<br>{total_meds}</div>", unsafe_allow_html=True)
col2.markdown(f"<div class='card'>📦 Total Quantity<br>{total_quantity}</div>", unsafe_allow_html=True)
col3.markdown(f"<div class='card'>⚠️ Low Stock Items<br>{low_stock_count}</div>", unsafe_allow_html=True)

# ------------------- Current Stock Table -------------------
st.subheader("📦 Current Stock")

def highlight_low_stock(row):
    return ['background-color: #fee2e2' if row['quantity'] < 10 else '' for _ in row]

st.dataframe(df.style.apply(highlight_low_stock, axis=1))

# ------------------- Low Stock Section -------------------
st.subheader("⚠️ Low Stock Alert (Qty < 10)")
low_stock = df[df["quantity"] < 10]

if not low_stock.empty:
    st.dataframe(low_stock.style.apply(highlight_low_stock, axis=1))
else:
    st.success("🎉 All medicines are sufficiently stocked!")

# ------------------- Search & Filter -------------------
st.subheader("🔍 Search / Filter Medicines")
search_term = st.text_input("Type medicine name to search")
if search_term:
    filtered_df = df[df["name"].str.contains(search_term, case=False, na=False)]
    st.dataframe(filtered_df.style.apply(highlight_low_stock, axis=1))
