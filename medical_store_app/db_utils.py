import sqlite3
import pandas as pd

DB_NAME = "medical_store.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def fetch_all(query, params=None):
    conn = get_connection()
    df = pd.read_sql_query(query, conn, params=params or [])
    conn.close()
    return df

def execute_query(query, params=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params or [])
    conn.commit()
    conn.close()

def insert_bulk(df):
    conn = get_connection()
    df.to_sql("medicines", conn, if_exists="append", index=False)
    conn.close()

