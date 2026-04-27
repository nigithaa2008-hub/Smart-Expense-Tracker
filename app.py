"""
==============================================
  SPENDWISE - Flask Backend (SQLite version)
==============================================
  Routes:
    GET  /                        → serve UI
    GET  /api/categories          → all categories
    GET  /api/transactions        → list transactions
    POST /api/transactions        → add transaction
    PUT  /api/transactions/<id>   → update transaction
    DELETE /api/transactions/<id> → delete transaction
    GET  /api/summary?period=...  → income/expense totals
    GET  /api/monthly-data        → last 6 months bar chart
    GET  /api/weekly-trend        → last 7 days line chart
    GET  /api/budgets             → get all budgets
    POST /api/budgets             → save budgets (bulk upsert)
    GET  /api/budget-status       → budget usage + alerts
==============================================
"""

from flask import Flask, render_template, request, jsonify
import sqlite3
import os
from datetime import datetime, timedelta

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), 'spendwise.db')


# ─────────────────────────────────────────────
#  Database helpers
# ─────────────────────────────────────────────

def get_db():
    """Open a database connection with row_factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables and seed categories if the DB doesn't exist."""
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with get_db() as conn:
        with open(schema_path, 'r') as f:
            conn.executescript(f.read())
    print("✅ Database initialised:", DB_PATH)


def row_to_dict(row):
    return dict(row) if row else None


# ─────────────────────────────────────────────
#  App startup
# ─────────────────────────────────────────────

if not os.path.exists(DB_PATH):
    init_db()


# ─────────────────────────────────────────────
#  UI route
# ─────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


# ─────────────────────────────────────────────
#  Categories
# ─────────────────────────────────────────────

@app.route('/api/categories', methods=['GET'])
def get_categories():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM categories ORDER BY type, label").fetchall()
    return jsonify([row_to_dict(r) for r in rows])


# ─────────────────────────────────────────────
#  Transactions — CRUD
# ─────────────────────────────────────────────

@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT t.id, t.type, t.amount, t.category_id,
                   c.label AS category_label, c.icon AS category_icon,
                   t.description, t.notes, t.date, t.created_at
            FROM transactions t
            JOIN categories c ON c.id = t.category_id
            ORDER BY t.date DESC, t.created_at DESC
        """).fetchall()
    return jsonify([row_to_dict(r) for r in rows])


@app.route('/api/transactions', methods=['POST'])
def add_transaction():
    data = request.json
    required = ['type', 'amount', 'category_id', 'date']
    if not all(k in data for k in required):
        return jsonify({'error': 'Missing required fields'}), 400

    with get_db() as conn:
        cur = conn.execute("""
            INSERT INTO transactions (type, amount, category_id, description, notes, date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data['type'],
            float(data['amount']),
            data['category_id'],
            data.get('description', ''),
            data.get('notes', ''),
            data['date']
        ))
        tx_id = cur.lastrowid
        conn.commit()

        row = conn.execute("""
            SELECT t.*, c.label AS category_label, c.icon AS category_icon
            FROM transactions t JOIN categories c ON c.id = t.category_id
            WHERE t.id = ?
        """, (tx_id,)).fetchone()

    return jsonify(row_to_dict(row)), 201


@app.route('/api/transactions/<int:tx_id>', methods=['PUT'])
def update_transaction(tx_id):
    data = request.json
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM transactions WHERE id = ?", (tx_id,)).fetchone()
        if not existing:
            return jsonify({'error': 'Not found'}), 404

        conn.execute("""
            UPDATE transactions
            SET type=?, amount=?, category_id=?, description=?, notes=?, date=?
            WHERE id=?
        """, (
            data['type'],
            float(data['amount']),
            data['category_id'],
            data.get('description', ''),
            data.get('notes', ''),
            data['date'],
            tx_id
        ))
        conn.commit()

        row = conn.execute("""
            SELECT t.*, c.label AS category_label, c.icon AS category_icon
            FROM transactions t JOIN categories c ON c.id = t.category_id
            WHERE t.id = ?
        """, (tx_id,)).fetchone()

    return jsonify(row_to_dict(row))


@app.route('/api/transactions/<int:tx_id>', methods=['DELETE'])
def delete_transaction(tx_id):
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM transactions WHERE id = ?", (tx_id,)).fetchone()
        if not existing:
            return jsonify({'error': 'Not found'}), 404
        conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
        conn.commit()
    return jsonify({'success': True, 'deleted_id': tx_id})


# ─────────────────────────────────────────────
#  Summary (dashboard stats)
# ─────────────────────────────────────────────

@app.route('/api/summary', methods=['GET'])
def get_summary():
    period = request.args.get('period', 'monthly')
    now = datetime.now()

    if period == 'daily':
        start_date = now.strftime('%Y-%m-%d')
    elif period == 'weekly':
        start_date = (now - timedelta(days=now.weekday())).strftime('%Y-%m-%d')
    else:
        start_date = now.strftime('%Y-%m-01')

    with get_db() as conn:
        income_row = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) AS total
            FROM transactions
            WHERE type='income' AND date >= ?
        """, (start_date,)).fetchone()

        expense_row = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) AS total
            FROM transactions
            WHERE type='expense' AND date >= ?
        """, (start_date,)).fetchone()

        count_row = conn.execute("""
            SELECT COUNT(*) AS total FROM transactions WHERE date >= ?
        """, (start_date,)).fetchone()

        cat_rows = conn.execute("""
            SELECT t.category_id, c.label, c.icon,
                   COALESCE(SUM(t.amount), 0) AS total
            FROM transactions t
            JOIN categories c ON c.id = t.category_id
            WHERE t.type='expense' AND t.date >= ?
            GROUP BY t.category_id
            ORDER BY total DESC
        """, (start_date,)).fetchall()

    income  = income_row['total']
    expenses = expense_row['total']

    by_category = {
        r['category_id']: {
            'label': r['label'],
            'icon':  r['icon'],
            'total': r['total']
        }
        for r in cat_rows
    }

    return jsonify({
        'income':            income,
        'expenses':          expenses,
        'net':               income - expenses,
        'by_category':       by_category,
        'period':            period,
        'transaction_count': count_row['total']
    })


# ─────────────────────────────────────────────
#  Monthly data (bar chart — last 6 months)
# ─────────────────────────────────────────────

@app.route('/api/monthly-data', methods=['GET'])
def get_monthly_data():
    now = datetime.now()
    months = []
    for i in range(5, -1, -1):
        d = now - timedelta(days=i * 30)
        months.append(d.strftime('%Y-%m'))

    result = {m: {'income': 0, 'expenses': 0} for m in months}

    with get_db() as conn:
        rows = conn.execute("""
            SELECT strftime('%Y-%m', date) AS month,
                   type,
                   COALESCE(SUM(amount), 0) AS total
            FROM transactions
            WHERE strftime('%Y-%m', date) IN ({})
            GROUP BY month, type
        """.format(','.join('?' * len(months))), months).fetchall()

    for r in rows:
        m = r['month']
        if m in result:
            if r['type'] == 'income':
                result[m]['income'] = r['total']
            else:
                result[m]['expenses'] = r['total']

    return jsonify(result)


# ─────────────────────────────────────────────
#  Weekly trend (line chart — last 7 days)
# ─────────────────────────────────────────────

@app.route('/api/weekly-trend', methods=['GET'])
def get_weekly_trend():
    now = datetime.now()
    days = {}
    day_list = []
    for i in range(6, -1, -1):
        d = (now - timedelta(days=i)).strftime('%Y-%m-%d')
        days[d] = {'income': 0, 'expenses': 0}
        day_list.append(d)

    with get_db() as conn:
        rows = conn.execute("""
            SELECT date, type, COALESCE(SUM(amount), 0) AS total
            FROM transactions
            WHERE date IN ({})
            GROUP BY date, type
        """.format(','.join('?' * len(day_list))), day_list).fetchall()

    for r in rows:
        d = r['date']
        if d in days:
            if r['type'] == 'income':
                days[d]['income'] = r['total']
            else:
                days[d]['expenses'] = r['total']

    return jsonify(days)


# ─────────────────────────────────────────────
#  Budgets
# ─────────────────────────────────────────────

@app.route('/api/budgets', methods=['GET'])
def get_budgets():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT b.category_id, b.amount, c.label, c.icon
            FROM budgets b JOIN categories c ON c.id = b.category_id
        """).fetchall()
    return jsonify({r['category_id']: r['amount'] for r in rows})


@app.route('/api/budgets', methods=['POST'])
def set_budgets():
    """Bulk upsert budgets. Body: { category_id: amount, ... }"""
    data = request.json  # { 'food': 8000, 'transport': 3000, ... }
    with get_db() as conn:
        # Clear existing and reinsert
        conn.execute("DELETE FROM budgets")
        for cat_id, amount in data.items():
            if amount and float(amount) > 0:
                conn.execute("""
                    INSERT INTO budgets (category_id, amount, updated_at)
                    VALUES (?, ?, datetime('now'))
                """, (cat_id, float(amount)))
        conn.commit()
    return jsonify({'success': True, 'saved': len(data)})


# ─────────────────────────────────────────────
#  Budget status + alerts
# ─────────────────────────────────────────────

@app.route('/api/budget-status', methods=['GET'])
def get_budget_status():
    now = datetime.now()
    month_start = now.strftime('%Y-%m-01')

    with get_db() as conn:
        budgets = conn.execute("""
            SELECT b.category_id, b.amount AS budget,
                   c.label, c.icon
            FROM budgets b JOIN categories c ON c.id = b.category_id
        """).fetchall()

        spent_rows = conn.execute("""
            SELECT category_id, COALESCE(SUM(amount), 0) AS spent
            FROM transactions
            WHERE type='expense' AND date >= ?
            GROUP BY category_id
        """, (month_start,)).fetchall()

    spent_map = {r['category_id']: r['spent'] for r in spent_rows}

    status = {}
    alerts = []

    for b in budgets:
        cat_id = b['category_id']
        budget = b['budget']
        spent  = spent_map.get(cat_id, 0)
        pct    = (spent / budget * 100) if budget > 0 else 0
        remaining = budget - spent

        status[cat_id] = {
            'label':     b['label'],
            'icon':      b['icon'],
            'budget':    budget,
            'spent':     spent,
            'pct':       round(pct, 1),
            'remaining': remaining
        }

        if pct >= 100:
            alerts.append({
                'type':     'exceeded',
                'category': cat_id,
                'label':    b['label'],
                'icon':     b['icon'],
                'pct':      round(pct, 1),
                'spent':    spent,
                'budget':   budget
            })
        elif pct >= 80:
            alerts.append({
                'type':     'warning',
                'category': cat_id,
                'label':    b['label'],
                'icon':     b['icon'],
                'pct':      round(pct, 1),
                'spent':    spent,
                'budget':   budget
            })

    return jsonify({'status': status, 'alerts': alerts})


# ─────────────────────────────────────────────
#  Run
# ─────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=True, port=5050)
