import sqlite3

# Connect to your existing database
conn = sqlite3.connect("medical_store.db")
c = conn.cursor()

# Check existing columns in 'medicines' table
c.execute("PRAGMA table_info(medicines)")
existing_cols = [row[1] for row in c.fetchall()]

# If 'brand_name' column is missing, add it
if "brand_name" not in existing_cols:
    c.execute("ALTER TABLE medicines ADD COLUMN brand_name TEXT")
    conn.commit()
    print(" Added 'brand_name' column to medicines table.")
else:
    print("'brand_name' column already exists.")

conn.close()
