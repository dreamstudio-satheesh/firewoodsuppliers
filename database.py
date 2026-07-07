import sqlite3
import shutil
import os
from datetime import datetime
from typing import Any

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db")
DB_PATH = os.path.join(DB_DIR, "billing.db")
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backup")

_conn: sqlite3.Connection | None = None


def get_connection() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        os.makedirs(DB_DIR, exist_ok=True)
        _conn = sqlite3.connect(DB_PATH)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA foreign_keys=ON")
    return _conn


def close():
    global _conn
    if _conn:
        _conn.close()
        _conn = None


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS company (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            name TEXT NOT NULL DEFAULT '',
            address TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            website TEXT DEFAULT '',
            bank_name TEXT DEFAULT '',
            bank_account TEXT DEFAULT '',
            bank_ifsc TEXT DEFAULT '',
            pan TEXT DEFAULT '',
            invoice_prefix TEXT DEFAULT 'BL',
            footer_line1 TEXT DEFAULT '',
            footer_line2 TEXT DEFAULT '',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS farmer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mobile TEXT DEFAULT '',
            address TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS customer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mobile TEXT DEFAULT '',
            address TEXT DEFAULT '',
            opening_balance REAL NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS vehicle (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_no TEXT NOT NULL UNIQUE,
            owner_name TEXT DEFAULT '',
            mobile TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sale_bill (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_no TEXT NOT NULL UNIQUE,
            customer_id INTEGER REFERENCES customer(id),
            customer_name TEXT DEFAULT '',
            customer_mobile TEXT DEFAULT '',
            vehicle_no TEXT DEFAULT '',
            product_name TEXT DEFAULT '',
            gross_weight REAL NOT NULL DEFAULT 0,
            tare_weight REAL NOT NULL DEFAULT 0,
            net_weight REAL NOT NULL DEFAULT 0,
            weight_unit TEXT DEFAULT 'Kg',
            rate REAL NOT NULL DEFAULT 0,
            amount REAL NOT NULL DEFAULT 0,
            bill_date TEXT NOT NULL,
            amount_in_words TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS receipt (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_no TEXT NOT NULL UNIQUE,
            bill_no TEXT REFERENCES sale_bill(bill_no),
            customer_id INTEGER REFERENCES customer(id),
            customer_name TEXT DEFAULT '',
            customer_mobile TEXT DEFAULT '',
            receipt_date TEXT NOT NULL,
            amount REAL NOT NULL DEFAULT 0,
            amount_in_words TEXT DEFAULT '',
            mode TEXT DEFAULT 'Cash',
            reference_no TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT DEFAULT '',
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        INSERT OR IGNORE INTO company (id, name, address, phone, email, website,
            bank_name, bank_account, bank_ifsc, pan, invoice_prefix,
            footer_line1, footer_line2)
            VALUES (1, 'Ragumani Transport & Fire Woods Suppliers',
            '',
            '', '', '',
            '', '', '', '',
            'BL', 'E. & O. E.', 'Thank you for your business!');

        INSERT OR IGNORE INTO users (id, username, password_hash, full_name, role)
        VALUES (1, 'admin', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'Administrator', 'admin');
    """)

    conn.commit()

    # Migrate existing database: add opening_balance if missing
    try:
        conn.execute("ALTER TABLE customer ADD COLUMN opening_balance REAL NOT NULL DEFAULT 0")
    except Exception:
        pass  # column already exists


def backup_database() -> str:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"billing_backup_{ts}.db")
    shutil.copy2(DB_PATH, backup_path)
    return backup_path


def _next_seq_no(table: str, column: str, prefix: str) -> str:
    conn = get_connection()
    cur = conn.cursor()
    year = datetime.now().strftime("%Y")
    pattern = f"{prefix}/{year}/%"
    cur.execute(
        f"SELECT {column} FROM {table} WHERE {column} LIKE ? ORDER BY id DESC LIMIT 1",
        (pattern,),
    )
    row = cur.fetchone()
    if row:
        parts = row[column].split("/")
        seq = int(parts[-1]) + 1
    else:
        seq = 1
    return f"{prefix}/{year}/{seq:06d}"


def get_next_bill_no(prefix: str = "BL") -> str:
    return _next_seq_no("sale_bill", "bill_no", prefix)


def get_next_receipt_no(prefix: str = "RC") -> str:
    return _next_seq_no("receipt", "receipt_no", prefix)
