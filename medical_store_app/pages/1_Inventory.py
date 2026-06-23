import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime

# ---------------- Page Config ----------------
st.set_page_config(page_title="Medical Inventory", page_icon="💊", layout="wide")

# ---------------- Database Setup ----------------
conn = sqlite3.connect("medical_store.db", check_same_thread=False)
c = conn.cursor()

# Inventory table (with brand_name added)
c.execute("""
CREATE TABLE IF NOT EXISTS medicines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    brand_name TEXT,
    batch_no TEXT,
    quantity INTEGER,
    price_per_unit REAL,
    gst_percent REAL,
    expiry_date TEXT
)
""")

# Billing history table
c.execute("""
CREATE TABLE IF NOT EXISTS billing_history (
    bill_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT,
    customer_mobile TEXT,
    medicine_name TEXT,
    quantity INTEGER,
    price_per_unit REAL,
    total_price REAL,
    gst_percent REAL,
    final_price REAL,
    bill_date TEXT
)
""")
conn.commit()

# ---------------- Helper Functions ----------------
def load_data():
    return pd.read_sql("SELECT * FROM medicines", conn)

def safe_parse_date(value):
    try:
        if value and isinstance(value, str):
            return date.fromisoformat(value)
    except Exception:
        pass
    return date.today()

# ---------------- Custom CSS ----------------
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; color: #000000; font-family: 'Poppins', sans-serif; }
    h1 { color: #066e91 !important; text-align: center; font-weight: 800; }
    .stButton>button { background: #066e91; color: white; border-radius: 10px; padding: 8px 20px; font-weight: bold; }
    .stButton>button:hover { background: #05536b; }
    .metric-card { padding: 12px; border-radius: 12px; background: #f8f9fa; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# ---------------- Dashboard Header ----------------
st.title("💊 Medical Store Inventory Dashboard")

df = load_data()

# ---------------- Quick Stats ----------------
col1, col2, col3, col4 = st.columns(4)
total_items = len(df)
low_stock = df[df["quantity"] < 10].shape[0] if not df.empty else 0
expired = df[df["expiry_date"] < datetime.today().strftime("%Y-%m-%d")].shape[0] if not df.empty else 0
total_stock = df["quantity"].sum() if not df.empty else 0
col1.metric("📦 Total Medicines", total_items)
col2.metric("💊 Total Stock (Qty)", total_stock)
col3.metric("⚠️ Low Stock", low_stock)
col4.metric("❌ Expired", expired)

# ---------------- Tabs ----------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📋 Inventory", "➕ Add Medicine", "✏️ Update/Delete",
    "📂 Bulk Upload", "🗑 Clear All Data", "🧾 Billing / Sales"
])

# ---------------- Tab 1: Inventory ----------------
with tab1:
    st.subheader("📋 Current Stock")
    df = load_data()
    if not df.empty:
        df["expiry_date"] = pd.to_datetime(df["expiry_date"], errors="coerce").dt.date

        def highlight_row(row):
            if pd.notnull(row["expiry_date"]) and row["expiry_date"] < datetime.today().date():
                return ['background-color: #ffcccc'] * len(row)  # Expired
            elif row["quantity"] < 10:
                return ['background-color: #fff3cd'] * len(row)  # Low stock
            return [''] * len(row)

        st.dataframe(df.style.apply(highlight_row, axis=1), use_container_width=True)
    else:
        st.info("No medicines found in inventory.")

# ---------------- Tab 2: Add Medicine ----------------
with tab2:
    st.subheader("➕ Add New Medicine")
    with st.form("add_medicine", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Medicine Name")
            brand_name = st.text_input("Brand Name")
            batch_no = st.text_input("Batch No")
            qty = st.number_input("Quantity", min_value=0, step=1)
        with col2:
            price = st.number_input("Price per unit 💰", min_value=0.0, step=0.1)
            gst = st.number_input("GST %", min_value=0.0, step=0.5, value=5.0)
            expiry = st.date_input("Expiry Date", value=date.today())

        submitted = st.form_submit_button("✅ Add Medicine")
        if submitted:
            if name and batch_no:
                c.execute("""INSERT INTO medicines (name,brand_name,batch_no,quantity,price_per_unit,gst_percent,expiry_date)
                             VALUES (?,?,?,?,?,?,?)""",
                          (name, brand_name, batch_no, qty, price, gst, expiry.strftime("%Y-%m-%d")))
                conn.commit()
                st.success(f"✅ {name} ({brand_name}) added successfully!")
                st.rerun()
            else:
                st.warning("⚠️ Please fill all required fields.")

# ---------------- Tab 3: Update/Delete ----------------
with tab3:
    st.subheader("✏️ Update or Delete Medicine")
    df = load_data()
    if not df.empty:
        med_to_update = st.selectbox("Select Medicine", df["name"].tolist())
        med_row = df[df["name"] == med_to_update].iloc[0]

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            new_qty = st.number_input("New Quantity", min_value=0, value=int(med_row["quantity"]))
        with col2:
            new_price = st.number_input("New Price per unit 💰", min_value=0.0,
                                        value=float(med_row["price_per_unit"]))
        with col3:
            new_expiry = st.date_input("New Expiry Date", value=safe_parse_date(med_row["expiry_date"]))
        with col4:
            new_gst = st.number_input("New GST %", min_value=0.0, step=0.5,
                                      value=float(med_row["gst_percent"] if med_row["gst_percent"] else 5.0))
        with col5:
            new_brand = st.text_input("New Brand Name", value=str(med_row["brand_name"]) if med_row["brand_name"] else "")

        colA, colB = st.columns(2)
        with colA:
            if st.button("💾 Update Selected"):
                c.execute("""UPDATE medicines SET quantity=?, price_per_unit=?, expiry_date=?, gst_percent=?, brand_name=? WHERE id=?""",
                          (new_qty, new_price, new_expiry.strftime("%Y-%m-%d"), new_gst, new_brand, int(med_row["id"])))
                conn.commit()
                st.success(f"✅ {med_to_update} updated successfully!")
                st.rerun()
        with colB:
            if st.button("🗑 Delete Selected"):
                c.execute("DELETE FROM medicines WHERE id=?", (int(med_row["id"]),))
                conn.commit()
                st.error(f"❌ {med_to_update} deleted successfully!")
                st.rerun()
    else:
        st.info("No medicines available to update/delete.")

# ---------------- Tab 4: Bulk Upload ----------------
with tab4:
    st.subheader("📂 Bulk Upload Medicines")
    st.info("➡️ Upload a CSV or Excel file with medicine details.")
    sample_data = pd.DataFrame({
        "name": ["Paracetamol", "Cough Syrup"],
        "brand_name": ["Cipla", "Zydus"],
        "batch_no": ["B001", "B002"],
        "quantity": [100, 50],
        "price_per_unit": [2.5, 45.0],
        "gst_percent": [5.0, 12.0],
        "expiry_date": ["2025-08-01", "2026-01-15"]
    })
    st.download_button("📥 Download Template (CSV)", data=sample_data.to_csv(index=False),
                       file_name="medicine_template.csv", mime="text/csv")

    uploaded_file = st.file_uploader("Upload your CSV/Excel file", type=["csv", "xlsx"])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                new_data = pd.read_csv(uploaded_file)
            else:
                new_data = pd.read_excel(uploaded_file)

            st.write("📋 **Preview of Uploaded Data:**")
            st.dataframe(new_data)

            required_cols = {"name", "brand_name", "batch_no", "quantity", "price_per_unit", "gst_percent", "expiry_date"}
            if not required_cols.issubset(set(new_data.columns)):
                st.error(f"❌ Invalid file format! Must contain columns: {required_cols}")
            else:
                if st.button("✅ Add to Database"):
                    all_exist = True  # Flag to check if all rows already exist

                    for _, row in new_data.iterrows():
                        # Check if batch_no already exists
                        c.execute("SELECT * FROM medicines WHERE batch_no = ?", (row["batch_no"],))
                        existing = c.fetchone()

                        if existing:
                            st.warning(f"ℹ️ Batch {row['batch_no']} already exists. Skipped.")
                        else:
                            c.execute("""INSERT INTO medicines (name, brand_name, batch_no, quantity, price_per_unit, gst_percent, expiry_date)
                                         VALUES (?,?,?,?,?,?,?)""",
                                      (row["name"], row["brand_name"], row["batch_no"], int(row["quantity"]),
                                       float(row["price_per_unit"]), float(row["gst_percent"]), str(row["expiry_date"])))
                            conn.commit()
                            st.success(f"✅ Batch {row['batch_no']} added successfully!")
                            all_exist = False

                    if all_exist:
                        st.info("ℹ️ All data is already saved in the database.")

                    st.rerun()
        except Exception as e:
            st.error(f"⚠️ Error while processing file: {e}")

# ---------------- Tab 5: Clear All Data ----------------
with tab5:
    st.subheader("🗑 Clear All Data")
    st.warning("⚠️ This will permanently delete **ALL medicines** from the database!")
    if st.button("🗑 Clear All Medicines"):
        c.execute("DELETE FROM medicines")
        conn.commit()
        st.error("❌ All medicines deleted successfully!")
        st.rerun()

# ---------------- Tab 6: Billing / Sales ----------------
with tab6:
    st.subheader("🧾 Sell Medicines")

    customer_name = st.text_input("👤 Customer Name")
    customer_mobile = st.text_input("📱 Customer Mobile")

    df = load_data()
    inventory_placeholder = st.empty()
    if not df.empty:
        inventory_placeholder.dataframe(df[["name", "brand_name", "quantity", "price_per_unit", "gst_percent"]])

        meds_to_sell = st.multiselect("Select Medicines to Sell", df["name"].tolist())
        if meds_to_sell and customer_name and customer_mobile:
            total_bill = 0
            sold_summary = []
            updated_rows = []

            for med_name in meds_to_sell:
                med_row = df[df["name"] == med_name].iloc[0]
                available_qty = int(med_row["quantity"])
                price_per_unit = float(med_row["price_per_unit"])
                gst_percent = float(med_row["gst_percent"]) if med_row["gst_percent"] else 5.0

                qty_to_sell = st.number_input(f"Quantity for {med_name}", min_value=1,
                                              max_value=available_qty if available_qty > 0 else 1, step=1,
                                              key=f"qty_{med_name}")

                base_price = qty_to_sell * price_per_unit
                gst_amount = base_price * (gst_percent / 100)
                total_price = base_price + gst_amount
                total_bill += total_price

                sold_summary.append({
                    "Medicine": med_name,
                    "Brand": med_row["brand_name"],
                    "Quantity": qty_to_sell,
                    "Unit Price (₹)": price_per_unit,
                    "Base Price (₹)": base_price,
                    "GST (%)": gst_percent,
                    "GST Amount (₹)": gst_amount,
                    "Total (₹)": total_price
                })
                updated_rows.append((available_qty - qty_to_sell, int(med_row["id"]), med_name, qty_to_sell,
                                     price_per_unit, base_price, gst_percent, total_price))

            st.markdown("### 🛒 Bill Summary")
            bill_df = pd.DataFrame(sold_summary)
            st.dataframe(bill_df, use_container_width=True)

            st.markdown(f"### 💰 **Total Payable: ₹{total_bill:.2f}**")

            if st.button("✅ Complete Sale (Sold)"):
                bill_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for new_qty, med_id, med_name, qty_sold, price_per_unit, base_price, gst_percent, total_price in updated_rows:
                    # Update inventory
                    c.execute("UPDATE medicines SET quantity=? WHERE id=?", (new_qty, med_id))
                    # Insert into billing history
                    c.execute("""INSERT INTO billing_history
                        (customer_name, customer_mobile, medicine_name, quantity, price_per_unit, total_price, gst_percent, final_price, bill_date)
                        VALUES (?,?,?,?,?,?,?,?,?)""",
                        (customer_name, customer_mobile, med_name, qty_sold, price_per_unit,
                         base_price, gst_percent, total_price, bill_date))
                conn.commit()
                st.success("✅ Sale completed and recorded in history!")

                # Refresh inventory
                df = load_data()
                inventory_placeholder.dataframe(df[["name", "brand_name", "quantity", "price_per_unit", "gst_percent"]])

        elif not customer_name or not customer_mobile:
            st.warning("⚠️ Please enter customer details before billing.")
    else:
        st.info("No medicines available for sale.")

    # ---------------- Show Billing History ----------------
    st.subheader("📜 Billing History")
    history_df = pd.read_sql("SELECT * FROM billing_history ORDER BY bill_id DESC", conn)
    st.dataframe(history_df, use_container_width=True)
