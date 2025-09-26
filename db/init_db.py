#!/usr/bin/env python3
import os, sqlite3

DB_PATH = os.environ.get("DATABASE_URL", "sqlite:///./db/dev.db").replace("sqlite:///", "")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# users table (opt-in)
cur.execute("""CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_id TEXT UNIQUE,
    consent INTEGER DEFAULT 0,
    opted_out INTEGER DEFAULT 0,
    ts TEXT
)""")

# templates table (manage realistic templates)
cur.execute("""CREATE TABLE IF NOT EXISTS templates (
    id TEXT PRIMARY KEY,
    text TEXT,
    created_at TEXT
)""")

# settings table (single-row-ish)
cur.execute("""CREATE TABLE IF NOT EXISTS settings (
    k TEXT PRIMARY KEY,
    v TEXT
)""")

# campaigns table - admin creates campaigns which bot picks up
cur.execute("""CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    mode TEXT,            -- 'dm' or 'channel'
    labelled INTEGER,     -- 0 realistic, 1 labelled
    template_id TEXT,     -- pick one template
    created_by TEXT,
    created_at TEXT,
    status TEXT DEFAULT 'pending',  -- pending, sending, sent, failed
    sent_at TEXT
)""")

# sims/clicks table (keep previous clicks schema)
cur.execute("""CREATE TABLE IF NOT EXISTS clicks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sim_id TEXT,
    user_id TEXT,
    user_agent TEXT,
    ip TEXT,
    submitted INTEGER DEFAULT 0,
    input_len INTEGER,
    entropy_est REAL,
    ts TEXT
)""")

conn.commit()
conn.close()
print("Initialized DB at:", DB_PATH)
