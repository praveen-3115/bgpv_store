import sqlite3
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, 'sassy_store.db')
SQL_FILE = os.path.join(BASE_DIR, 'sassy_store_backup.sql')

def create_schema(cursor):
    """Create all required tables in SQLite."""
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admin (
        admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        profile_image TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        description TEXT,
        category TEXT,
        price REAL,
        image TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cart (
        cart_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products (product_id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        razorpay_order_id TEXT,
        razorpay_payment_id TEXT,
        amount REAL,
        payment_status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        delivery_address TEXT,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        product_name TEXT,
        quantity INTEGER,
        price REAL,
        address TEXT,
        FOREIGN KEY (order_id) REFERENCES orders (order_id),
        FOREIGN KEY (product_id) REFERENCES products (product_id)
    );
    """)

def import_backup_data(cursor, sql_path=SQL_FILE):
    """Import data from MySQL backup file if available."""
    if not os.path.exists(sql_path):
        print(f"Backup file not found at {sql_path}. Skipping data import.")
        return

    # Try utf-16le then utf-8
    sql = None
    for enc in ['utf-16le', 'utf-8', 'latin-1']:
        try:
            with open(sql_path, 'r', encoding=enc) as f:
                content = f.read()
                if "CREATE TABLE" in content or "INSERT INTO" in content:
                    sql = content
                    break
        except Exception:
            continue

    if not sql:
        print("Could not read backup SQL file.")
        return

    # Turn off foreign keys temporarily for bulk insert
    cursor.execute("PRAGMA foreign_keys = OFF;")

    valid_tables = ['admin', 'users', 'products', 'cart', 'orders', 'order_items']
    for m in re.finditer(r'INSERT INTO `?(\w+)`? VALUES\s*(.*?);', sql, re.DOTALL):
        table = m.group(1)
        values = m.group(2).strip()

        if table in valid_tables:
            # Check if table already has rows to avoid duplicate inserts
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            if cursor.fetchone()[0] > 0:
                print(f"Table '{table}' already contains data. Skipping insert.")
                continue

            # Convert MySQL escaped quotes \' to SQLite standard ''
            values = values.replace(r"\'", "''")
            insert_query = f"INSERT INTO {table} VALUES {values};"
            try:
                cursor.execute(insert_query)
                print(f"Successfully migrated data into '{table}'")
            except Exception as e:
                print(f"Error migrating into '{table}': {e}")

    cursor.execute("PRAGMA foreign_keys = ON;")

def init_database(db_path=DB_FILE, force_recreate=False):
    """Initialize SQLite database, tables and initial data."""
    if force_recreate and os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed old database file: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    create_schema(cursor)
    import_backup_data(cursor)

    conn.commit()

    print("\n--- Current SQLite Database Status ---")
    for tbl in ['admin', 'users', 'products', 'cart', 'orders', 'order_items']:
        cursor.execute(f"SELECT COUNT(*) FROM {tbl}")
        count = cursor.fetchone()[0]
        print(f"  - {tbl}: {count} records")

    conn.close()
    print(f"\nDatabase ready at: {db_path}")

if __name__ == '__main__':
    import sys
    force = '--force' in sys.argv
    init_database(force_recreate=force)
