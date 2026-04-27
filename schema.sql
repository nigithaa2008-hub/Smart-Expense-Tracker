-- ============================================
--   SPENDWISE - SQLite Database Schema
-- ============================================

-- Drop existing tables if re-initializing
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS budgets;
DROP TABLE IF EXISTS categories;

-- ============================================
-- TABLE: categories
-- Stores all income/expense category definitions
-- ============================================
CREATE TABLE categories (
    id          TEXT PRIMARY KEY,         -- e.g. 'food', 'salary'
    label       TEXT NOT NULL,            -- e.g. 'Food & Dining'
    icon        TEXT NOT NULL,            -- emoji icon
    type        TEXT NOT NULL             -- 'income' or 'expense'
                CHECK(type IN ('income','expense'))
);

-- ============================================
-- TABLE: transactions
-- Every income or expense entry
-- ============================================
CREATE TABLE transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    type        TEXT NOT NULL             -- 'income' or 'expense'
                CHECK(type IN ('income','expense')),
    amount      REAL NOT NULL             -- positive number
                CHECK(amount > 0),
    category_id TEXT NOT NULL,            -- FK -> categories.id
    description TEXT,                     -- short description
    notes       TEXT,                     -- optional longer note
    date        TEXT NOT NULL,            -- ISO date: YYYY-MM-DD
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- ============================================
-- TABLE: budgets
-- Monthly budget limits per expense category
-- ============================================
CREATE TABLE budgets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id TEXT NOT NULL UNIQUE,     -- FK -> categories.id
    amount      REAL NOT NULL             -- monthly limit
                CHECK(amount > 0),
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- ============================================
-- INDEXES for performance
-- ============================================
CREATE INDEX idx_transactions_date     ON transactions(date);
CREATE INDEX idx_transactions_type     ON transactions(type);
CREATE INDEX idx_transactions_category ON transactions(category_id);

-- ============================================
-- SEED: default categories
-- ============================================
INSERT INTO categories (id, label, icon, type) VALUES
    ('food',          'Food & Dining',  '🍽️',  'expense'),
    ('transport',     'Transport',      '🚗',  'expense'),
    ('shopping',      'Shopping',       '🛍️',  'expense'),
    ('health',        'Health',         '🏥',  'expense'),
    ('entertainment', 'Entertainment',  '🎬',  'expense'),
    ('utilities',     'Utilities',      '💡',  'expense'),
    ('education',     'Education',      '📚',  'expense'),
    ('rent',          'Rent/EMI',       '🏠',  'expense'),
    ('other_exp',     'Other Expense',  '💼',  'expense'),
    ('salary',        'Salary',         '💰',  'income'),
    ('freelance',     'Freelance',      '💻',  'income'),
    ('investment',    'Investment',     '📈',  'income'),
    ('gift',          'Gift',           '🎁',  'income'),
    ('other_inc',     'Other Income',   '💵',  'income');
