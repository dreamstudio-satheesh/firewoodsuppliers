from database import get_connection


def get_customer_statement(
    customer_id: int, customer_name: str, date_from: str, date_to: str
) -> dict:
    conn = get_connection()

    # Opening balance: all bills and receipts before date_from
    billed_before = conn.execute(
        """SELECT COALESCE(SUM(amount), 0) FROM sale_bill
           WHERE customer_id=? AND bill_date < ? AND status='active'""",
        (customer_id, date_from),
    ).fetchone()[0]

    received_before = conn.execute(
        """SELECT COALESCE(SUM(amount), 0) FROM receipt
           WHERE customer_id=? AND receipt_date < ? AND status='active'""",
        (customer_id, date_from),
    ).fetchone()[0]

    opening_balance = billed_before - received_before

    # All transactions (bills + receipts) in date range, sorted by date
    bills = conn.execute(
        """SELECT bill_date AS tx_date, bill_no AS ref_no, 'Bill' AS type,
                  amount AS debit, 0 AS credit
           FROM sale_bill
           WHERE customer_id=? AND bill_date BETWEEN ? AND ? AND status='active'""",
        (customer_id, date_from, date_to),
    ).fetchall()

    receipts = conn.execute(
        """SELECT receipt_date AS tx_date, receipt_no AS ref_no, 'Receipt' AS type,
                  0 AS debit, amount AS credit
           FROM receipt
           WHERE customer_id=? AND receipt_date BETWEEN ? AND ? AND status='active'""",
        (customer_id, date_from, date_to),
    ).fetchall()

    # Merge and sort by date
    all_txns = [dict(r) for r in bills] + [dict(r) for r in receipts]
    all_txns.sort(key=lambda x: x["tx_date"])

    # Running balance
    balance = opening_balance
    for t in all_txns:
        balance += t["debit"] - t["credit"]
        t["balance"] = balance

    closing_balance = opening_balance + sum(
        t["debit"] - t["credit"] for t in all_txns
    )

    return {
        "customer_id": customer_id,
        "customer_name": customer_name,
        "date_from": date_from,
        "date_to": date_to,
        "opening_balance": opening_balance,
        "closing_balance": closing_balance,
        "transactions": all_txns,
    }


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


