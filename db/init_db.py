#!/usr/bin/env python3
"""
Initialize the sqlite DB schema used in development.
Run: python db/init_db.py
"""
import os
import sqlite3

DB_PATH = os.environ.get("DATABASE_URL", "sqlite:///./db/dev.db").replace("sqlite:///", "")

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id TEXT UNIQUE,
                consent INTEGER DEFAULT 0,
                opted_out INTEGER DEFAULT 0,
                ts TEXT
               )""")
cur.execute("""CREATE TABLE IF NOT EXISTS sims (
                id TEXT PRIMARY KEY,
                template TEXT,
                ts TEXT
               )""")
cur.execute("""CREATE TABLE IF NOT EXISTS clicks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sim_id TEXT,
                user_agent TEXT,
                ip TEXT,
                ts TEXT
               )""")

conn.commit()
conn.close()
print("Initialized DB at:", DB_PATH)
