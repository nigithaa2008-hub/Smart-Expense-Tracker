"""
run.py — One-click launcher for Spendwise SQL version.
Usage: python run.py
"""
import os, sys, subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)

DB = os.path.join(BASE, 'spendwise.db')
if not os.path.exists(DB):
    print("🌱 No database found — seeding demo data...")
    subprocess.run([sys.executable, 'seed.py'], check=True)

print("\n" + "═"*48)
print("  💸  SPENDWISE  —  Smart Expense Tracker")
print("  🗄️   Database : SQLite  (spendwise.db)")
print("  🌐  Open      : http://localhost:5050")
print("═"*48 + "\n")
subprocess.run([sys.executable, 'app.py'])
