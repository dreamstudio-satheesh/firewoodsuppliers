from database import get_connection


def search_farmers(query: str = "") -> list[dict]:
    conn = get_connection()
    if query:
        rows = conn.execute(
            """SELECT * FROM farmer
               WHERE name LIKE ? OR mobile LIKE ?
               ORDER BY name""",
            (f"%{query}%", f"%{query}%"),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM farmer ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def get_farmer(farmer_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM farmer WHERE id=?", (farmer_id,)).fetchone()
    return dict(row) if row else None


def add_farmer(name: str, mobile: str = "", address: str = "") -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO farmer (name, mobile, address) VALUES (?, ?, ?)",
        (name.strip(), mobile.strip(), address.strip()),
    )
    conn.commit()
    return cur.lastrowid


def update_farmer(farmer_id: int, name: str, mobile: str = "", address: str = ""):
    conn = get_connection()
    conn.execute(
        """UPDATE farmer SET name=?, mobile=?, address=?,
           updated_at=CURRENT_TIMESTAMP WHERE id=?""",
        (name.strip(), mobile.strip(), address.strip(), farmer_id),
    )
    conn.commit()


def delete_farmer(farmer_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM farmer WHERE id=?", (farmer_id,))
    conn.commit()


def get_all_farmers() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT id, name, mobile FROM farmer ORDER BY name").fetchall()
    return [dict(r) for r in rows]
