# fix_orders_schema.py
import sqlite3, shutil, os, sys

DB = "nightlife.db"

if not os.path.exists(DB):
    print("ERROR: database file not found at", DB)
    sys.exit(1)

bak = DB + ".bak"
shutil.copyfile(DB, bak)
print("Backup created:", bak)

con = sqlite3.connect(DB)
cur = con.cursor()

# Get existing columns in orders
cur.execute("PRAGMA table_info(orders);")
cols_info = cur.fetchall()
existing_cols = [r[1] for r in cols_info]
print("Existing orders columns:", existing_cols)

# Columns we expect (from your models). Use types compatible with SQLite.
expected = {
    "vendor_id": "INTEGER",
    "club_id": "INTEGER",
    "user_id": "INTEGER",
    "user_name": "TEXT",
    "user_phone": "TEXT",
    "user_address": "TEXT",
    "subtotal": "REAL DEFAULT 0.0",
    "platform_fee": "REAL DEFAULT 0.0",
    "delivery_fee": "REAL DEFAULT 0.0",
    "packing_fee": "REAL DEFAULT 0.0",
    "tax_amount": "REAL DEFAULT 0.0",
    "discount": "REAL DEFAULT 0.0",
    "total": "REAL DEFAULT 0.0",
    "payment_method": "TEXT DEFAULT 'COD'",
    "payment_id": "TEXT",
    "payment_meta": "TEXT",
    "status": "TEXT DEFAULT 'PENDING'",
    "created_at": "DATETIME"
}

added = []
for col, col_def in expected.items():
    if col not in existing_cols:
        stmt = f"ALTER TABLE orders ADD COLUMN {col} {col_def};"
        try:
            print("Adding column:", col, "definition:", col_def)
            cur.execute(stmt)
            con.commit()
            added.append(col)
        except Exception as e:
            print("Failed to add", col, "-", e)

if not added:
    print("No columns needed to be added. orders table already has expected columns.")
else:
    print("Added columns:", added)

# Show final schema
cur.execute("PRAGMA table_info(orders);")
final = cur.fetchall()
print("\nFinal orders schema:")
for r in final:
    print(f" - {r[1]} ({r[2]})  notnull={r[3]} dflt={r[4]} pk={r[5]}")

cur.close()
con.close()
print("\nDone. Restart your backend and test the failing endpoint.")
