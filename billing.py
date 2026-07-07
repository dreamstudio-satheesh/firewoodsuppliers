from database import get_connection


def create_sale_bill(
    bill_no: str,
    customer_id: int,
    customer_name: str,
    customer_mobile: str,
    vehicle_no: str,
    gross_weight: float,
    tare_weight: float,
    net_weight: float,
    weight_unit: str,
    rate: float,
    amount: float,
    bill_date: str,
    product_name: str = "Firewood",
    amount_in_words: str = "",
    notes: str = "",
) -> int:
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO sale_bill (bill_no, customer_id, customer_name, customer_mobile,
           vehicle_no, product_name, gross_weight, tare_weight, net_weight,
           weight_unit, rate, amount, bill_date, amount_in_words, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            bill_no, customer_id, customer_name, customer_mobile,
            vehicle_no, product_name, gross_weight, tare_weight, net_weight,
            weight_unit, rate, amount, bill_date, amount_in_words, notes,
        ),
    )
    conn.commit()
    return cur.lastrowid


def get_sale_bill(bill_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM sale_bill WHERE id=?", (bill_id,)).fetchone()
    return dict(row) if row else None


def search_sale_bills(
    query: str = "",
    date_from: str = "",
    date_to: str = "",
    status: str = "active",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    conn = get_connection()

    count_sql = "SELECT COUNT(*) FROM sale_bill WHERE status=? "
    params: list = [status]
    if query:
        count_sql += "AND (bill_no LIKE ? OR customer_name LIKE ? OR customer_mobile LIKE ?) "
        params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])
    if date_from:
        count_sql += "AND bill_date >= ? "
        params.append(date_from)
    if date_to:
        count_sql += "AND bill_date <= ? "
        params.append(date_to)
    total = conn.execute(count_sql, params).fetchone()[0]

    data_sql = "SELECT * FROM sale_bill WHERE status=? "
    data_params: list = [status]
    if query:
        data_sql += "AND (bill_no LIKE ? OR customer_name LIKE ? OR customer_mobile LIKE ?) "
        data_params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])
    if date_from:
        data_sql += "AND bill_date >= ? "
        data_params.append(date_from)
    if date_to:
        data_sql += "AND bill_date <= ? "
        data_params.append(date_to)

    data_sql += "ORDER BY id DESC LIMIT ? OFFSET ?"
    data_params.extend([page_size, (page - 1) * page_size])
    rows = conn.execute(data_sql, data_params).fetchall()
    return [dict(r) for r in rows], total


def cancel_sale_bill(bill_id: int):
    conn = get_connection()
    conn.execute("UPDATE sale_bill SET status='cancelled' WHERE id=?", (bill_id,))
    conn.commit()


def delete_sale_bill(bill_id: int):
    conn = get_connection()
    bill = conn.execute("SELECT bill_no FROM sale_bill WHERE id=?", (bill_id,)).fetchone()
    if not bill:
        return
    conn.execute("DELETE FROM receipt WHERE bill_no=?", (bill["bill_no"],))
    conn.execute("DELETE FROM sale_bill WHERE id=?", (bill_id,))
    conn.commit()


def get_entries_for_consolidated_bill(
    customer_id: int, date_from: str, date_to: str
) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT id, bill_no, bill_date, vehicle_no, gross_weight, tare_weight,
                  net_weight, rate, amount
           FROM sale_bill
           WHERE customer_id=? AND bill_date BETWEEN ? AND ? AND status='active'
           ORDER BY bill_date, id""",
        (customer_id, date_from, date_to),
    ).fetchall()
    return [dict(r) for r in rows]


def get_dashboard_data() -> dict:
    conn = get_connection()
    today_sales = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM sale_bill WHERE bill_date=date('now') AND status='active'"
    ).fetchone()[0]
    total_customers = conn.execute("SELECT COUNT(*) FROM customer").fetchone()[0]
    total_farmers = conn.execute("SELECT COUNT(*) FROM farmer").fetchone()[0]
    total_bills = conn.execute(
        "SELECT COUNT(*) FROM sale_bill WHERE status='active'"
    ).fetchone()[0]
    recent = conn.execute(
        "SELECT id, bill_no, customer_name, amount, bill_date FROM sale_bill WHERE status='active' ORDER BY id DESC LIMIT 5"
    ).fetchall()
    return {
        "today_sales": today_sales,
        "total_customers": total_customers,
        "total_farmers": total_farmers,
        "total_bills": total_bills,
        "recent_bills": [dict(r) for r in recent],
    }
