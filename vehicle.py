from database import get_connection


def search_vehicles(query: str = "") -> list[dict]:
    conn = get_connection()
    if query:
        rows = conn.execute(
            """SELECT * FROM vehicle
               WHERE vehicle_no LIKE ? OR owner_name LIKE ? OR mobile LIKE ?
               ORDER BY vehicle_no""",
            (f"%{query}%", f"%{query}%", f"%{query}%"),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM vehicle ORDER BY vehicle_no").fetchall()
    return [dict(r) for r in rows]


def get_vehicle(vehicle_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM vehicle WHERE id=?", (vehicle_id,)).fetchone()
    return dict(row) if row else None


def add_vehicle(vehicle_no: str, owner_name: str = "", mobile: str = "") -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO vehicle (vehicle_no, owner_name, mobile) VALUES (?, ?, ?)",
        (vehicle_no.strip().upper(), owner_name.strip(), mobile.strip()),
    )
    conn.commit()
    return cur.lastrowid


def update_vehicle(vehicle_id: int, vehicle_no: str, owner_name: str = "", mobile: str = ""):
    conn = get_connection()
    conn.execute(
        """UPDATE vehicle SET vehicle_no=?, owner_name=?, mobile=?,
           updated_at=CURRENT_TIMESTAMP WHERE id=?""",
        (vehicle_no.strip().upper(), owner_name.strip(), mobile.strip(), vehicle_id),
    )
    conn.commit()


def delete_vehicle(vehicle_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM vehicle WHERE id=?", (vehicle_id,))
    conn.commit()


def get_all_vehicles() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, vehicle_no, owner_name FROM vehicle ORDER BY vehicle_no"
    ).fetchall()
    return [dict(r) for r in rows]
