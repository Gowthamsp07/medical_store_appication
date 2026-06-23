import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import uuid
from collections import defaultdict

# -------------------------
# Connect to DB
# -------------------------
conn = sqlite3.connect("medical_store.db", check_same_thread=False)
c = conn.cursor()

# -------------------------
# Create sales tables if not exist
# -------------------------
c.execute("""
CREATE TABLE IF NOT EXISTS sales (
    sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_no TEXT UNIQUE,
    customer_name TEXT,
    customer_mobile TEXT,
    subtotal REAL,
    total_gst REAL,
    extra_tax REAL,
    grand_total REAL,
    sale_date TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS sale_items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER,
    medicine_id INTEGER,
    medicine_name TEXT,
    company_name TEXT,
    quantity INTEGER,
    price_per_unit REAL,
    gst_percent REAL,
    gst_amount REAL,
    line_total REAL,
    free_item INTEGER DEFAULT 0,
    FOREIGN KEY(sale_id) REFERENCES sales(sale_id)
)
""")
conn.commit()

# -------------------------
# Page Config & Styling
# -------------------------
st.set_page_config(page_title="Billing System", page_icon="🧾", layout="wide")

st.markdown("""
<style>
.stApp { background: linear-gradient(to bottom right, #f0f4f8, #ffffff); color: #000; font-family: 'Segoe UI', sans-serif; }
.header { text-align: center; font-weight: 800; color: #066e91; font-size: 32px; margin-bottom: 15px; }
.info-box { background: #e6f3fa; border: 1px solid #b3d9ff; padding: 15px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
.bill-table th { background: #066e91 !important; color: #fff !important; padding: 10px !important; font-size: 14px; }
.bill-table td { padding: 10px !important; text-align: center !important; color: #000 !important; font-size: 13px; }
.totals-box { background: #e6f3fa; border: 1px solid #b3d9ff; padding: 15px; border-radius: 12px; font-weight: 600; width: 400px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
.complete-btn { background-color: #066e91; color: #fff; padding: 12px 20px; border-radius: 8px; font-weight: 700; transition: background-color 0.3s; }
.complete-btn:hover { background-color: #054f6b; }
.tab-content { padding: 20px; border-radius: 10px; }
.summary-table th { background: #066e91 !important; color: #fff !important; }
.summary-table td { background: #f8f9fa; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="header">💊 Billing System</div>', unsafe_allow_html=True)

# -------------------------
# Helper Functions
# -------------------------
def load_medicines():
    """Load medicines from DB and parse expiry_date."""
    dfm = pd.read_sql("""
        SELECT id, name, brand_name AS company_name, quantity, price_per_unit, gst_percent, expiry_date
        FROM medicines
    """, conn)
    if "expiry_date" in dfm.columns:
        dfm["expiry_date"] = pd.to_datetime(dfm["expiry_date"], errors="coerce").dt.date
    return dfm

def generate_bill_no():
    return f"BILL-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:8]}"

def consolidate_bill_lines(bill_lines):
    """Combine duplicates of same medicine in one line."""
    combined = defaultdict(lambda: {
        "quantity": 0, "gst_amount": 0.0, "line_total": 0.0, "price_per_unit": 0.0,
        "medicine_id": None, "medicine_name": None, "company_name": None, "gst_percent": 0.0, "free_item": 0
    })
    
    for bl in bill_lines:
        key = (bl["medicine_id"], bl["price_per_unit"], bl["free_item"])
        combined[key]["medicine_id"] = bl["medicine_id"]
        combined[key]["medicine_name"] = bl["medicine_name"]
        combined[key]["company_name"] = bl["company_name"]
        combined[key]["price_per_unit"] = bl["price_per_unit"]
        combined[key]["gst_percent"] = bl["gst_percent"]
        combined[key]["free_item"] = bl["free_item"]
        combined[key]["quantity"] += bl["quantity"]
        combined[key]["gst_amount"] += bl["gst_amount"]
        combined[key]["line_total"] += bl["line_total"]
    
    return list(combined.values())

def save_sale(header, items):
    """Save sale header and line items to DB."""
    c.execute("""
        INSERT INTO sales (bill_no, customer_name, customer_mobile, subtotal, total_gst, extra_tax, grand_total, sale_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        header["bill_no"], header["customer_name"], header["customer_mobile"],
        header["subtotal"], header["total_gst"], header["extra_tax"],
        header["grand_total"], header["sale_date"]
    ))
    sale_id = c.lastrowid

    for it in items:
        c.execute("""
            INSERT INTO sale_items (sale_id, medicine_id, medicine_name, company_name, quantity, price_per_unit, gst_percent, gst_amount, line_total, free_item)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sale_id, it["medicine_id"], it["medicine_name"], it["company_name"], it["quantity"],
            it["price_per_unit"], it["gst_percent"], it["gst_amount"],
            it["line_total"], it["free_item"]
        ))
    conn.commit()
    return sale_id

def update_stock_decrement(items):
    for it in items:
        c.execute("UPDATE medicines SET quantity = quantity - ? WHERE id = ?", (it["quantity"], it["medicine_id"]))
    conn.commit()

def restore_stock_from_sale(bill_no):
    sale_rows = pd.read_sql("""
        SELECT si.medicine_id, si.quantity 
        FROM sale_items si 
        JOIN sales s ON si.sale_id = s.sale_id 
        WHERE s.bill_no=?
    """, conn, params=(bill_no,))
    for _, r in sale_rows.iterrows():
        c.execute("UPDATE medicines SET quantity = quantity + ? WHERE id = ?", (int(r["quantity"]), int(r["medicine_id"])))
    conn.commit()

def delete_sale(bill_no):
    # Get sale_id
    c.execute("SELECT sale_id FROM sales WHERE bill_no = ?", (bill_no,))
    sale_id = c.fetchone()[0]
    # Delete items
    c.execute("DELETE FROM sale_items WHERE sale_id = ?", (sale_id,))
    # Delete sale
    c.execute("DELETE FROM sales WHERE bill_no = ?", (bill_no,))
    conn.commit()

def load_sales_history(start_date=None, end_date=None):
    query = "SELECT * FROM sales"
    params = []
    if start_date:
        query += " WHERE sale_date >= ?"
        params.append(start_date)
        if end_date:
            query += " AND sale_date <= ?"
            params.append(end_date)
    elif end_date:
        query += " WHERE sale_date <= ?"
        params.append(end_date)
    query += " ORDER BY sale_date DESC"
    df = pd.read_sql(query, conn, params=params)
    return df

def load_sale_items(sale_id):
    df = pd.read_sql("""
        SELECT medicine_name, company_name, quantity, price_per_unit, gst_percent, gst_amount, line_total, free_item
        FROM sale_items WHERE sale_id = ?
    """, conn, params=(sale_id,))
    return df

def load_sales_summary(period='daily'):
    if period == 'daily':
        group_by = "sale_date"
    elif period == 'weekly':
        group_by = "strftime('%Y-%W', sale_date)"
    elif period == 'monthly':
        group_by = "strftime('%Y-%m', sale_date)"
    else:
        group_by = "sale_date"

    df = pd.read_sql(f"""
        SELECT {group_by} AS period, SUM(grand_total) AS total_sales, SUM(subtotal) AS total_subtotal, SUM(total_gst) AS total_gst, SUM(extra_tax) AS total_extra_tax
        FROM sales
        GROUP BY period
        ORDER BY period DESC
    """, conn)
    return df

def load_top_medicines(limit=10):
    df = pd.read_sql("""
        SELECT si.medicine_name, SUM(si.quantity) AS total_quantity, SUM(si.line_total) AS total_revenue
        FROM sale_items si
        WHERE si.free_item = 0
        GROUP BY si.medicine_name
        ORDER BY total_revenue DESC
        LIMIT ?
    """, conn, params=(limit,))
    return df

# -------------------------
# Tabs
# -------------------------
tab1, tab2, tab3 = st.tabs(["🧾 Billing", "📜 Bill History", "📊 Sales Summary"])

############################
# TAB 1 - Billing
############################
with tab1:
    st.markdown('<div class="info-box">Select medicines, set quantities/prices, optionally mark items free, add extra tax and customer details, then complete sale.</div>', unsafe_allow_html=True)

    medicines_df = load_medicines()
    if medicines_df.empty:
        st.warning("No medicines found in inventory. Add medicines in Inventory page first.")
        st.stop()

    selected = st.multiselect("Select medicines to add to bill", medicines_df["name"].tolist(), key="billing_select")
    bill_lines, subtotal, total_gst, grand_total = [], 0.0, 0.0, 0.0
    today = datetime.now().date()

    if selected:
        cols = st.columns(min(len(selected), 4))
        for i, name in enumerate(selected):
            row = medicines_df[medicines_df["name"] == name].iloc[0]
            col = cols[i % len(cols)]

            if "expiry_date" in row and pd.notnull(row["expiry_date"]) and row["expiry_date"] < today:
                col.error(f"⚠️ {name} is EXPIRED ({row['expiry_date']}). Cannot add.")
                continue

            stock = int(row["quantity"] or 0)
            default_price = float(row["price_per_unit"] or 0.0)
            default_gst = float(row["gst_percent"] or 0.0)

            with col:
                st.markdown(f"**{name} ({row['company_name']})**")
                qty = st.number_input(f"Qty (stock: {stock})", min_value=0, max_value=stock, value=0, key=f"qty_{name}")
                price = st.number_input(f"Price/unit", min_value=0.0, value=default_price, step=0.1, key=f"price_{name}")
                gst_pct = st.number_input(f"GST%", min_value=0.0, max_value=100.0, value=default_gst, step=0.5, key=f"gst_{name}")
                free_flag = st.checkbox("Mark FREE", key=f"free_{name}")

            if qty > 0:
                if free_flag:
                    line_price = gst_amount = line_total = 0.0
                else:
                    line_price = price
                    line_sub = qty * line_price
                    gst_amount = line_sub * (gst_pct / 100.0)
                    line_total = line_sub + gst_amount

                bill_lines.append({
                    "medicine_id": int(row["id"]),
                    "medicine_name": name,
                    "company_name": row["company_name"],
                    "quantity": int(qty),
                    "price_per_unit": float(line_price),
                    "gst_percent": float(gst_pct),
                    "gst_amount": float(gst_amount),
                    "line_total": float(line_total),
                    "free_item": 1 if free_flag else 0
                })

                subtotal += (qty * line_price)
                total_gst += gst_amount
                grand_total += line_total

    if bill_lines:
        bill_lines = consolidate_bill_lines(bill_lines)

    extra_tax = 0.0
    if bill_lines:
        extra_tax = st.number_input("Additional Tax / Service Charge (₹)", min_value=0.0, value=0.0, step=1.0)

    customer_name = ""
    customer_mobile = ""
    if bill_lines:
        st.markdown("#### Customer Details")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            customer_name = st.text_input("Customer Name")
        with col_c2:
            customer_mobile = st.text_input("Customer Mobile")

    # Live Bill Display
    st.markdown("### Live Bill")
    if bill_lines:
        bill_display = []
        for bl in bill_lines:
            bill_display.append({
                "Medicine": bl["medicine_name"],
                "Company": bl["company_name"],
                "Qty": bl["quantity"],
                "Price/unit": f"₹{bl['price_per_unit']:.2f}" if bl["free_item"] == 0 else "FREE",
                "GST%": f"{bl['gst_percent']:.1f}%",
                "GST Amt": f"₹{bl['gst_amount']:.2f}",
                "Line Total": f"₹{bl['line_total']:.2f}" if bl["free_item"] == 0 else "FREE"
            })
        df_bill = pd.DataFrame(bill_display)
        st.markdown(df_bill.to_html(index=False, classes="bill-table"), unsafe_allow_html=True)

        final_total = grand_total + float(extra_tax)
        tcol, bcol = st.columns([1, 1])
        with tcol:
            st.markdown(f"""
                <div class="totals-box">
                <strong>Subtotal:</strong> ₹{subtotal:.2f}<br>
                <strong>Total GST:</strong> ₹{total_gst:.2f}<br>
                <strong>Extra Tax:</strong> ₹{extra_tax:.2f}<br>
                <strong style="font-size:18px;">Grand Total: ₹{final_total:.2f}</strong>
                </div>
            """, unsafe_allow_html=True)

        with bcol:
            can_complete = (len(bill_lines) > 0) and (customer_name.strip() != "")
            if st.button("Complete Sale", disabled=not can_complete, key="complete_sale"):
                bill_no = generate_bill_no()
                sale_date = datetime.now().isoformat()
                header = {
                    "bill_no": bill_no,
                    "customer_name": customer_name,
                    "customer_mobile": customer_mobile,
                    "subtotal": subtotal,
                    "total_gst": total_gst,
                    "extra_tax": extra_tax,
                    "grand_total": final_total,
                    "sale_date": sale_date
                }
                save_sale(header, bill_lines)
                update_stock_decrement(bill_lines)
                st.success(f"Sale completed! Bill No: {bill_no}")
                st.rerun()

############################
# TAB 2 - Bill History
############################
with tab2:
    st.markdown('<div class="info-box">View past bills, filter by date, view details, and cancel bills if needed.</div>', unsafe_allow_html=True)

    # Date filters
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        start_date = st.date_input("Start Date", value=None)
    with col_d2:
        end_date = st.date_input("End Date", value=None)

    start_str = start_date.isoformat() if start_date else None
    end_str = end_date.isoformat() if end_date else None

    sales_df = load_sales_history(start_str, end_str)
    if sales_df.empty:
        st.info("No sales found for the selected period.")
    else:
        st.markdown("### Sales History")
        display_df = sales_df[["bill_no", "customer_name", "customer_mobile", "grand_total", "sale_date"]]
        display_df["grand_total"] = display_df["grand_total"].apply(lambda x: f"₹{x:.2f}")
        st.dataframe(display_df)

        # View details and cancel
        selected_bill = st.selectbox("Select Bill to View/Cancel", sales_df["bill_no"].tolist())
        if selected_bill:
            sale_row = sales_df[sales_df["bill_no"] == selected_bill].iloc[0]
            sale_id = int(sale_row["sale_id"])
            items_df = load_sale_items(sale_id)

            st.markdown("#### Bill Details")
            details_display = []
            for _, it in items_df.iterrows():
                details_display.append({
                    "Medicine": it["medicine_name"],
                    "Company": it["company_name"],
                    "Qty": it["quantity"],
                    "Price/unit": f"₹{it['price_per_unit']:.2f}" if it["free_item"] == 0 else "FREE",
                    "GST%": f"{it['gst_percent']:.1f}%",
                    "GST Amt": f"₹{it['gst_amount']:.2f}",
                    "Line Total": f"₹{it['line_total']:.2f}" if it["free_item"] == 0 else "FREE"
                })
            df_details = pd.DataFrame(details_display)
            st.markdown(df_details.to_html(index=False, classes="bill-table"), unsafe_allow_html=True)

            st.markdown(f"""
                <div class="totals-box">
                <strong>Subtotal:</strong> ₹{sale_row['subtotal']:.2f}<br>
                <strong>Total GST:</strong> ₹{sale_row['total_gst']:.2f}<br>
                <strong>Extra Tax:</strong> ₹{sale_row['extra_tax']:.2f}<br>
                <strong style="font-size:18px;">Grand Total: ₹{sale_row['grand_total']:.2f}</strong>
                </div>
            """, unsafe_allow_html=True)

            if st.button("Cancel This Bill", key="cancel_bill"):
                restore_stock_from_sale(selected_bill)
                delete_sale(selected_bill)
                st.success(f"Bill {selected_bill} cancelled and stock restored.")
                st.rerun()

############################
# TAB 3 - Sales Summary
############################
with tab3:
    st.markdown('<div class="info-box">View sales summaries by period and top-selling medicines.</div>', unsafe_allow_html=True)

    period = st.selectbox("Summary Period", ["daily", "weekly", "monthly"])

    summary_df = load_sales_summary(period)
    if summary_df.empty:
        st.info("No sales data available.")
    else:
        st.markdown("### Sales Summary")
        summary_df["total_sales"] = summary_df["total_sales"].apply(lambda x: f"₹{x:.2f}")
        summary_df["total_subtotal"] = summary_df["total_subtotal"].apply(lambda x: f"₹{x:.2f}")
        summary_df["total_gst"] = summary_df["total_gst"].apply(lambda x: f"₹{x:.2f}")
        summary_df["total_extra_tax"] = summary_df["total_extra_tax"].apply(lambda x: f"₹{x:.2f}")
        st.markdown(summary_df.to_html(index=False, classes="summary-table"), unsafe_allow_html=True)

    st.markdown("### Top Selling Medicines")
    top_df = load_top_medicines()
    if top_df.empty:
        st.info("No sales data for top medicines.")
    else:
        top_df["total_revenue"] = top_df["total_revenue"].apply(lambda x: f"₹{x:.2f}")
        st.markdown(top_df.to_html(index=False, classes="summary-table"), unsafe_allow_html=True)