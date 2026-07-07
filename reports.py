from database import get_connection


def daily_sales(date: str | None = None) -> list[dict]:
    from datetime import date as dt_date
    if date is None:
        date = dt_date.today().isoformat()
    conn = get_connection()
    rows = conn.execute(
        """SELECT id, bill_no, customer_name, amount
           FROM sale_bill WHERE bill_date=? AND status='active'
           ORDER BY id""",
        (date,),
    ).fetchall()
    return [dict(r) for r in rows]


def date_range_sales(from_date: str, to_date: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT bill_date, COUNT(*) as count, SUM(amount) as total
           FROM sale_bill WHERE bill_date BETWEEN ? AND ? AND status='active'
           GROUP BY bill_date ORDER BY bill_date""",
        (from_date, to_date),
    ).fetchall()
    return [dict(r) for r in rows]


def customer_sales_report(customer_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT bill_no, bill_date, amount, status
           FROM sale_bill WHERE customer_id=? ORDER BY id DESC""",
        (customer_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def sales_register(from_date: str, to_date: str, period: str = "day") -> list[dict]:
    conn = get_connection()
    if period == "month":
        group_col = "strftime('%Y-%m', bill_date)"
        label_col = group_col + " AS period"
        order = group_col
    else:
        group_col = "bill_date"
        label_col = group_col + " AS period"
        order = group_col

    sql = f"""
        SELECT {label_col},
               COUNT(*) as bill_count,
               ROUND(SUM(amount), 2) as total
        FROM sale_bill
        WHERE bill_date BETWEEN ? AND ? AND status='active'
        GROUP BY {group_col}
        ORDER BY {order}
    """
    rows = conn.execute(sql, (from_date, to_date)).fetchall()
    return [dict(r) for r in rows]


