import sqlite3

def init_db():
    conn = sqlite3.connect("medical_store.db")
    c = conn.cursor()

    # Create medicines table
    c.execute("""
    CREATE TABLE IF NOT EXISTS medicines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        batch_no TEXT,
        quantity INTEGER,
        price_per_unit REAL,
        expiry_date DATE
    )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")

if __name__ == "__main__":
    init_db()
