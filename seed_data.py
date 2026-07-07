import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_connection, init_db


def seed():
    init_db()
    conn = get_connection()

    conn.executescript("""
        DELETE FROM receipt;
        DELETE FROM sale_bill;
        DELETE FROM customer;
        DELETE FROM farmer;
        DELETE FROM vehicle;
        DELETE FROM settings;
        DELETE FROM users;
        DELETE FROM company;
    """)

    conn.execute("""INSERT INTO company (id, name, address, phone, email, website,
                    bank_name, bank_account, bank_ifsc, pan, invoice_prefix,
                    footer_line1, footer_line2)
                    VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "Ragumani Transport & Fire Woods Suppliers",
            "Your Business Address\nCity, State - PIN",
            "98765 43210",
            "info@firewoodseller.com",
            "www.firewoodseller.com",
            "Your Bank",
            "1234567890123456",
            "IFSC0001234",
            "",
            "BL",
            "E. & O. E.",
            "Thank you for your business!",
        ),
    )

    pw_hash = hashlib.sha256(b"admin123").hexdigest()
    conn.execute(
        "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
        ("admin", pw_hash, "Administrator", "admin"),
    )

    farmers = [
        ("Ramasamy", "98765 11111", "Village A, Erode District"),
        ("Murugan", "98765 22222", "Village B, Salem District"),
        ("Selvam", "98765 33333", "Village C, Dharmapuri District"),
        ("Kumar", "98765 44444", "Village D, Krishnagiri District"),
    ]
    for name, mobile, address in farmers:
        conn.execute(
            "INSERT INTO farmer (name, mobile, address) VALUES (?, ?, ?)",
            (name, mobile, address),
        )

    customers = [
        ("Sri Balaji Plywoods", "98422 12345", "12, Industrial Area, Coimbatore"),
        ("Anand Timber Mart", "98422 23456", "45, Main Road, Erode"),
        ("Karthik Wood Works", "98422 34567", "89, Market Road, Salem"),
        ("Star Furniture Pvt Ltd", "98422 45678", "Plot 5, Avinashi Road, Tiruppur"),
    ]
    for name, mobile, address in customers:
        conn.execute(
            "INSERT INTO customer (name, mobile, address) VALUES (?, ?, ?)",
            (name, mobile, address),
        )

    vehicles = [
        ("TN38AB1234", "Ramasamy", "98765 11111"),
        ("TN38CD5678", "Murugan", "98765 22222"),
        ("TN38EF9012", "Selvam", "98765 33333"),
    ]
    for vno, owner, mob in vehicles:
        conn.execute(
            "INSERT INTO vehicle (vehicle_no, owner_name, mobile) VALUES (?, ?, ?)",
            (vno, owner, mob),
        )

    conn.commit()
    print("Database seeded successfully!")
    print("  Company: Ragumani Transport & Fire Woods Suppliers")
    print(f"  Farmers: {len(farmers)}")
    print(f"  Customers: {len(customers)}")

    print(f"  Vehicles: {len(vehicles)}")
    print("  Admin password: admin123")


if __name__ == "__main__":
    seed()
