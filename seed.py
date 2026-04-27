"""
seed.py — Populate the SQLite database with realistic demo data.
Run once: python seed.py
"""

import sqlite3
import os
import random
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), 'spendwise.db')
SCHEMA  = os.path.join(os.path.dirname(__file__), 'schema.sql')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_db() as conn:
        with open(SCHEMA) as f:
            conn.executescript(f.read())
    print("✅ Schema created")


def seed():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("🗑️  Old database removed")

    init_db()

    now = datetime.now()

    # ── Expense transactions ──────────────────────────────────
    expense_data = [
        ('food',          [800, 1200, 650, 900, 450, 1100, 780, 320, 560, 980, 430, 670]),
        ('transport',     [350, 180, 420, 260, 310, 150, 480]),
        ('shopping',      [2500, 1800, 950, 3200, 700]),
        ('health',        [500, 1200, 350, 800]),
        ('entertainment', [600, 350, 450, 200, 900]),
        ('utilities',     [1500, 800, 2000, 1200]),
        ('rent',          [15000, 15000]),
        ('education',     [2000, 3500, 800]),
        ('other_exp',     [300, 700, 150]),
    ]

    expense_descs = {
        'food':          ['Swiggy order', 'Grocery - BigBasket', 'Restaurant dinner',
                          'Cafe latte', 'Street food', 'Zomato delivery', 'Supermarket'],
        'transport':     ['Uber ride', 'Ola cab', 'Petrol fill-up', 'Metro recharge',
                          'Auto rickshaw', 'Bus pass', 'Train ticket'],
        'shopping':      ['Amazon order', 'Clothing - Myntra', 'Electronics - Croma',
                          'Home decor', 'Flipkart purchase', 'Sports gear'],
        'health':        ['Apollo pharmacy', 'Gym membership', 'Doctor consultation',
                          'Lab tests', 'Health supplement'],
        'entertainment': ['Netflix subscription', 'Movie tickets - PVR', 'Spotify premium',
                          'OTT bundle', 'Gaming top-up'],
        'utilities':     ['Electricity bill', 'Internet - Airtel', 'Mobile recharge',
                          'Water bill', 'Gas cylinder'],
        'rent':          ['Monthly rent', 'Maintenance charge'],
        'education':     ['Udemy course', 'Book purchase', 'Online workshop',
                          'Certification fee'],
        'other_exp':     ['Miscellaneous', 'Donation', 'Stationery'],
    }

    # ── Income transactions ───────────────────────────────────
    income_data = [
        ('salary',     [75000, 75000, 75000]),
        ('freelance',  [12000, 8500, 5000, 15000]),
        ('investment', [3500, 2200]),
        ('gift',       [1000, 5000]),
        ('other_inc',  [800]),
    ]

    income_descs = {
        'salary':     ['Monthly salary', 'Salary credit'],
        'freelance':  ['Client project payment', 'Consulting fee', 'Design project',
                       'Web development contract'],
        'investment': ['Stock dividend', 'FD interest', 'Mutual fund return'],
        'gift':       ['Birthday gift', 'Festival bonus', 'Family gift'],
        'other_inc':  ['Cashback credit', 'Referral bonus'],
    }

    transactions = []

    for cat, amounts in expense_data:
        for amount in amounts:
            days_ago = random.randint(0, 60)
            date = (now - timedelta(days=days_ago)).strftime('%Y-%m-%d')
            transactions.append((
                'expense', amount, cat,
                random.choice(expense_descs[cat]), '', date
            ))

    for cat, amounts in income_data:
        for i, amount in enumerate(amounts):
            days_ago = i * 28 + random.randint(0, 5)
            date = (now - timedelta(days=days_ago)).strftime('%Y-%m-%d')
            transactions.append((
                'income', amount, cat,
                random.choice(income_descs[cat]), '', date
            ))

    # ── Budgets ───────────────────────────────────────────────
    budgets = [
        ('food',          8000),
        ('transport',     3000),
        ('shopping',      5000),
        ('health',        2000),
        ('entertainment', 2000),
        ('utilities',     3000),
        ('rent',          16000),
        ('education',     4000),
    ]

    with get_db() as conn:
        conn.executemany("""
            INSERT INTO transactions (type, amount, category_id, description, notes, date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, transactions)

        conn.executemany("""
            INSERT INTO budgets (category_id, amount) VALUES (?, ?)
        """, budgets)

        conn.commit()

    print(f"✅ Seeded {len(transactions)} transactions")
    print(f"✅ Seeded {len(budgets)} budgets")
    print(f"📁 Database: {DB_PATH}")


if __name__ == '__main__':
    seed()
