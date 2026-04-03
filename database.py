import sqlite3
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

class SmartDatabase:
    def __init__(self, db_name: str = "smart_tracker.db"):
        self.db_name = db_name
        self.conn = None
        self.init_database()

    def init_database(self):
        """Initialize the database with the required tables for the smart tracker."""
        self.conn = sqlite3.connect(self.db_name)
        cursor = self.conn.cursor()

        # 1. Transactions Table (with auto-categorisation support)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,       -- auto-categorised or manual
                transaction_type TEXT NOT NULL, -- INCOME or EXPENSE
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Daily Limits / Budgets Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month_year TEXT UNIQUE NOT NULL, -- e.g., '2026-04'
                total_monthly_limit REAL NOT NULL,
                daily_safe_limit REAL NOT NULL
            )
        """)

        # 3. Bill Calendar & Reminders Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_name TEXT NOT NULL,
                amount REAL NOT NULL,
                due_date TEXT NOT NULL,      -- e.g., '2026-04-15'
                is_paid INTEGER DEFAULT 0    -- 0 for false, 1 for true
            )
        """)

        # 4. Funds Table (Medical Fund, Emergency Fund, etc.)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS funds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fund_name TEXT UNIQUE NOT NULL,
                target_amount REAL NOT NULL,
                current_amount REAL DEFAULT 0
            )
        """)

        # 5. Alerts & Notifications Table (Smart hints, warnings, AI Summaries)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,    -- 'WARNING', 'AI_SUMMARY', 'SAVINGS_SUGGESTION'
                message TEXT NOT NULL,
                date TEXT DEFAULT CURRENT_TIMESTAMP,
                is_read INTEGER DEFAULT 0
            )
        """)

        self.conn.commit()

        # Initialize Default Funds if they don't exist
        self._init_default_funds()

    def _init_default_funds(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO funds (fund_name, target_amount, current_amount) VALUES ('Medical Fund', 5000.0, 0)")
            cursor.execute("INSERT OR IGNORE INTO funds (fund_name, target_amount, current_amount) VALUES ('Auto Savings', 10000.0, 0)")
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error initializing default funds: {e}")

    # --- Transaction & Categorization Methods ---
    def add_transaction(self, date: str, amount: float, description: str, transaction_type: str = "EXPENSE") -> str:
        """Adds a transaction and auto-categorizes it based on keywords."""
        category = self._auto_categorize(description)
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO transactions (date, amount, category, transaction_type, description)
            VALUES (?, ?, ?, ?, ?)
        """, (date, amount, category, transaction_type, description))
        self.conn.commit()
        
        # Check if we broke the daily limit
        self._check_smart_warnings(date, amount)
        
        return category

    def _auto_categorize(self, description: str) -> str:
        """Simple rule-based auto categorization logic."""
        desc = description.lower()
        if any(word in desc for word in ['hospital', 'pharmacy', 'doctor', 'clinic', 'medicine']):
            return 'Medical'
        elif any(word in desc for word in ['supermarket', 'grocery', 'food', 'restaurant', 'coffee']):
            return 'Food & Dining'
        elif any(word in desc for word in ['uber', 'taxi', 'bus', 'train', 'fuel', 'gas']):
            return 'Transport'
        elif any(word in desc for word in ['netflix', 'movie', 'game', 'spotify']):
            return 'Entertainment'
        elif any(word in desc for word in ['electric', 'water', 'internet', 'bill']):
            return 'Utilities'
        return 'General'

    # --- Daily Safe Limit & Smart Warning Methods ---
    def set_monthly_budget(self, month_year: str, total_limit: float):
        """Calculates and sets the Daily Safe Limit based on the monthly budget."""
        # Simple days in month calc (assume 30 for simplicity)
        daily_safe_limit = total_limit / 30.0 
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO budgets (month_year, total_monthly_limit, daily_safe_limit)
            VALUES (?, ?, ?)
        """, (month_year, total_limit, daily_safe_limit))
        self.conn.commit()

    def _check_smart_warnings(self, date: str, latest_amount: float):
        """Generates a smart warning if daily expenses exceed the daily safe limit."""
        month_year = date[:7] # e.g., '2026-04'
        cursor = self.conn.cursor()
        
        # Get daily limit
        cursor.execute("SELECT daily_safe_limit FROM budgets WHERE month_year = ?", (month_year,))
        result = cursor.fetchone()
        if not result:
            return
        daily_limit = result[0]

        # Get total expenses for today
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE date = ? AND transaction_type = 'EXPENSE'", (date,))
        today_total = cursor.fetchone()[0] or 0

        # Smart Alert Logic
        if today_total > daily_limit:
            msg = f"Smart Warning: You have exceeded your daily safe limit of ${daily_limit:.2f}. Total spent today: ${today_total:.2f}."
            cursor.execute("INSERT INTO alerts (alert_type, message) VALUES ('WARNING', ?)", (msg,))
            self.conn.commit()

    # --- Bill Calendar & Reminders ---
    def add_bill(self, name: str, amount: float, due_date: str):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO bills (bill_name, amount, due_date) VALUES (?, ?, ?)", (name, amount, due_date))
        self.conn.commit()

    def get_upcoming_bills(self) -> List[Tuple]:
        cursor = self.conn.cursor()
        today = datetime.now().strftime('%Y-%m-%d')
        # Get bills from today up to 7 days in the future
        next_week = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        cursor.execute("SELECT * FROM bills WHERE due_date BETWEEN ? AND ? AND is_paid = 0 ORDER BY due_date", (today, next_week))
        return cursor.fetchall()

    def mark_bill_paid(self, bill_id: int):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE bills SET is_paid = 1 WHERE id = ?", (bill_id,))
        self.conn.commit()

    # --- Funds (Medical / Savings) ---
    def update_fund(self, fund_name: str, amount_to_add: float):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE funds SET current_amount = current_amount + ? WHERE fund_name = ?", (amount_to_add, fund_name))
        self.conn.commit()

    def get_funds(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM funds")
        return cursor.fetchall()

    # --- Auto Savings Suggestion ---
    def generate_savings_suggestion(self):
        """Analyzes expenses and suggests a savings amount."""
        cursor = self.conn.cursor()
        # Mock logic: Suggest saving 10% of total income if expenses are lower
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE transaction_type = 'INCOME'")
        income = cursor.fetchone()[0] or 0
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE transaction_type = 'EXPENSE'")
        expense = cursor.fetchone()[0] or 0
        
        balance = income - expense
        if balance > 0:
            suggested_savings = balance * 0.20 # Suggest saving 20% of remaining balance
            msg = f"Auto Savings Suggestion: You have a healthy balance. We suggest transferring ${suggested_savings:.2f} to your savings fund."
            cursor.execute("INSERT INTO alerts (alert_type, message) VALUES ('SAVINGS_SUGGESTION', ?)", (msg,))
            self.conn.commit()
            return msg
        return "Not enough balance to suggest savings right now."

    # --- Weekly AI Summary (Mocked logic) ---
    def generate_weekly_ai_summary(self):
        """Generates a summary of the past 7 days."""
        cursor = self.conn.cursor()
        last_week = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        cursor.execute("SELECT category, SUM(amount) FROM transactions WHERE date >= ? AND transaction_type = 'EXPENSE' GROUP BY category", (last_week,))
        expenses_by_cat = cursor.fetchall()
        
        if not expenses_by_cat:
            summary = "AI Summary: No expenses recorded in the last 7 days. Keep it up!"
        else:
            highest_cat = max(expenses_by_cat, key=lambda x: x[1])
            summary = f"AI Summary: Your highest spending category this week was '{highest_cat[0]}' with ${highest_cat[1]:.2f}. Consider cutting back here next week."
        
        cursor.execute("INSERT INTO alerts (alert_type, message) VALUES ('AI_SUMMARY', ?)", (summary,))
        self.conn.commit()
        return summary
    
    # --- Statistics ---
    def get_statistics(self):
        """Returns total spending categorized."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT category, SUM(amount) FROM transactions WHERE transaction_type = 'EXPENSE' GROUP BY category")
        return cursor.fetchall()
    
    def get_unread_alerts(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM alerts WHERE is_read = 0 ORDER BY date DESC")
        alerts = cursor.fetchall()
        # Mark as read
        for alert in alerts:
            cursor.execute("UPDATE alerts SET is_read = 1 WHERE id = ?", (alert[0],))
        self.conn.commit()
        return alerts

    def close(self):
        if self.conn:
            self.conn.close()
