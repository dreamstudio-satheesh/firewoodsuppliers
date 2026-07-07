import json
import os
from database import get_connection

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")


def load_json_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE) as f:
            return json.load(f)
    return {}


def save_json_settings(data: dict):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_json(key: str, default=None):
    return load_json_settings().get(key, default)


def set_json(key: str, value):
    d = load_json_settings()
    d[key] = value
    save_json_settings(d)


HARDCODED_NAME = "Ragumani Transport & Fire Woods Suppliers"


def get_company() -> dict:
    conn = get_connection()
    row = conn.execute("SELECT * FROM company WHERE id=1").fetchone()
    data = dict(row) if row else {}
    data["name"] = HARDCODED_NAME
    return data


def save_company(data: dict):
    conn = get_connection()
    current = conn.execute("SELECT * FROM company WHERE id=1").fetchone()
    if current:
        merged = dict(current)
        merged.update(data)
    else:
        merged = data
    merged["id"] = 1
    merged["name"] = HARDCODED_NAME
    conn.execute("""UPDATE company SET
        name=:name, address=:address, phone=:phone,
        email=:email, website=:website, bank_name=:bank_name,
        bank_account=:bank_account, bank_ifsc=:bank_ifsc, pan=:pan,
        invoice_prefix=:invoice_prefix, footer_line1=:footer_line1,
        footer_line2=:footer_line2, updated_at=CURRENT_TIMESTAMP
        WHERE id=1""", merged)
    conn.commit()


def get_db_setting(key: str, default=""):
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_db_setting(key: str, value: str):
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value)
    )
    conn.commit()
