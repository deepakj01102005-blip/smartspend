import sqlite3
import os
from flask import g

# This is where the database file will be saved
DB_PATH = os.path.join(os.path.dirname(__file__), "instance", "data.db")


def get_db():
    # If we don't have a connection yet for this request, create one
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        # This lets us access columns by name like row["amount"] instead of row[2]
        g.db.row_factory = sqlite3.Row
    return g.db


def init_db():
    # Create the instance folder if it doesn't exist
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Create tables only if they don't already exist
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            type        TEXT NOT NULL,
            category    TEXT NOT NULL,
            amount      REAL NOT NULL,
            description TEXT,
            date        TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            category      TEXT NOT NULL UNIQUE,
            monthly_limit REAL NOT NULL
        )
    """)

    conn.commit()

    # Only add sample data if the database is empty
    count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    if count == 0:
        add_sample_data(conn)

    conn.close()


def add_sample_data(conn):
    # Adding some realistic sample transactions so the dashboard looks good
    sample_transactions = [
        # This month
        ("income",  "Salary",        52000, "Monthly salary",      "2026-05-01"),
        ("income",  "Freelance",      8000, "Website project",     "2026-05-10"),
        ("expense", "Rent",          10000, "Monthly rent",        "2026-05-05"),
        ("expense", "Food & Dining",  3200, "Groceries and eating out", "2026-05-08"),
        ("expense", "Transport",      1500, "Cab and petrol",      "2026-05-12"),
        ("expense", "Shopping",       4500, "Clothes and Amazon",  "2026-05-15"),
        ("expense", "Utilities",      1200, "Electricity and wifi", "2026-05-07"),
        ("expense", "Entertainment",   800, "Netflix and movies",  "2026-05-20"),
        ("expense", "Healthcare",     1000, "Doctor visit",        "2026-05-18"),

        # Last month
        ("income",  "Salary",        50000, "Monthly salary",      "2026-04-01"),
        ("income",  "Freelance",      5000, "Logo design",         "2026-04-15"),
        ("expense", "Rent",          10000, "Monthly rent",        "2026-04-05"),
        ("expense", "Food & Dining",  2800, "Groceries",           "2026-04-10"),
        ("expense", "Transport",      1200, "Petrol",              "2026-04-12"),
        ("expense", "Shopping",       6000, "Phone accessories",   "2026-04-20"),
        ("expense", "Utilities",      1100, "Bills",               "2026-04-07"),
        ("expense", "Entertainment",   600, "Spotify and OTT",     "2026-04-25"),

        # 2 months ago
        ("income",  "Salary",        50000, "Monthly salary",      "2026-03-01"),
        ("expense", "Rent",          10000, "Monthly rent",        "2026-03-05"),
        ("expense", "Food & Dining",  3500, "Dining out",          "2026-03-15"),
        ("expense", "Transport",      1800, "Travel",              "2026-03-20"),
        ("expense", "Shopping",       2000, "Books and stationery","2026-03-22"),
        ("expense", "Utilities",       900, "Bills",               "2026-03-08"),

        # 3 months ago
        ("income",  "Salary",        50000, "Monthly salary",      "2026-02-01"),
        ("expense", "Rent",          10000, "Monthly rent",        "2026-02-05"),
        ("expense", "Food & Dining",  2500, "Groceries",           "2026-02-10"),
        ("expense", "Transport",      1000, "Metro and cab",       "2026-02-18"),
        ("expense", "Healthcare",     2500, "Medical checkup",     "2026-02-20"),
        ("expense", "Utilities",      1000, "Bills",               "2026-02-06"),

        # 4 months ago
        ("income",  "Salary",        48000, "Monthly salary",      "2026-01-01"),
        ("expense", "Rent",          10000, "Monthly rent",        "2026-01-05"),
        ("expense", "Food & Dining",  3000, "Groceries",           "2026-01-12"),
        ("expense", "Transport",      1300, "Cab rides",           "2026-01-15"),
        ("expense", "Shopping",       5000, "New year shopping",   "2026-01-20"),
        ("expense", "Utilities",      1100, "Bills",               "2026-01-07"),

        # 5 months ago
        ("income",  "Salary",        48000, "Monthly salary",      "2025-12-01"),
        ("expense", "Rent",          10000, "Monthly rent",        "2025-12-05"),
        ("expense", "Food & Dining",  4000, "Festive meals",       "2025-12-20"),
        ("expense", "Shopping",       8000, "Christmas shopping",  "2025-12-22"),
        ("expense", "Transport",      2000, "Holiday travel",      "2025-12-25"),
        ("expense", "Utilities",      1300, "Bills",               "2025-12-08"),
    ]

    conn.executemany(
        "INSERT INTO transactions (type, category, amount, description, date) VALUES (?, ?, ?, ?, ?)",
        sample_transactions
    )

    # Default budget limits for each category
    sample_budgets = [
        ("Rent",          10000),
        ("Food & Dining",  5000),
        ("Transport",      2000),
        ("Shopping",       5000),
        ("Utilities",      2000),
        ("Entertainment",  1500),
        ("Healthcare",     3000),
    ]

    conn.executemany(
        "INSERT OR IGNORE INTO budgets (category, monthly_limit) VALUES (?, ?)",
        sample_budgets
    )

    conn.commit()
