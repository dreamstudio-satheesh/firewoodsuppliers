from database import get_connection


def search_customers(query: str = "") -> list[dict]:
    conn = get_connection()
    if query:
        rows = conn.execute(
            """SELECT * FROM customer
               WHERE name LIKE ? OR mobile LIKE ?
               ORDER BY name""",
            (f"%{query}%", f"%{query}%"),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM customer ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def get_customer(customer_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM customer WHERE id=?", (customer_id,)).fetchone()
    return dict(row) if row else None


def add_customer(name: str, mobile: str = "", address: str = "") -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO customer (name, mobile, address) VALUES (?, ?, ?)",
        (name.strip(), mobile.strip(), address.strip()),
    )
    conn.commit()
    return cur.lastrowid


def update_customer(customer_id: int, name: str, mobile: str = "", address: str = ""):
    conn = get_connection()
    conn.execute(
        """UPDATE customer SET name=?, mobile=?, address=?,
           updated_at=CURRENT_TIMESTAMP WHERE id=?""",
        (name.strip(), mobile.strip(), address.strip(), customer_id),
    )
    conn.commit()


def delete_customer(customer_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM customer WHERE id=?", (customer_id,))
    conn.commit()


def get_all_customers() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT id, name, mobile FROM customer ORDER BY name").fetchall()
    return [dict(r) for r in rows]
