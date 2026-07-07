from database import get_connection


def create_receipt(
    receipt_no: str,
    bill_no: str,
    customer_id: int,
    customer_name: str,
    customer_mobile: str,
    receipt_date: str,
    amount: float,
    amount_in_words: str = "",
    mode: str = "Cash",
    reference_no: str = "",
    notes: str = "",
) -> int:
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO receipt (receipt_no, bill_no, customer_id, customer_name,
           customer_mobile, receipt_date, amount, amount_in_words, mode,
           reference_no, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            receipt_no, bill_no, customer_id, customer_name, customer_mobile,
            receipt_date, amount, amount_in_words, mode, reference_no, notes,
        ),
    )
    conn.commit()
    return cur.lastrowid


def get_receipt(receipt_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM receipt WHERE id=?", (receipt_id,)).fetchone()
    return dict(row) if row else None


def search_receipts(
    query: str = "",
    date_from: str = "",
    date_to: str = "",
    status: str = "active",
) -> list[dict]:
    conn = get_connection()
    sql = "SELECT * FROM receipt WHERE status=? "
    params: list = [status]

    if query:
        sql += "AND (receipt_no LIKE ? OR bill_no LIKE ? OR customer_name LIKE ? OR customer_mobile LIKE ?) "
        params.extend([f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"])
    if date_from:
        sql += "AND receipt_date >= ? "
        params.append(date_from)
    if date_to:
        sql += "AND receipt_date <= ? "
        params.append(date_to)

    sql += "ORDER BY id DESC"
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def cancel_receipt(receipt_id: int):
    conn = get_connection()
    conn.execute("UPDATE receipt SET status='cancelled' WHERE id=?", (receipt_id,))
    conn.commit()
