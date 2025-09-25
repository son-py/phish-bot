#!/usr/bin/env python3
"""
Flask landing app for phishing simulations.
Landing URL format: /l/<sim_id>
Logs clicks to the same sqlite DB used by the bot.
"""

import os
import sqlite3
from datetime import datetime
from flask import Flask, request, render_template, redirect, url_for, abort
from dotenv import load_dotenv

# Load .env in project root if present
if os.path.exists("../.env"):
    load_dotenv("../.env")

DATABASE_PATH = os.environ.get("DATABASE_URL", "sqlite:///./db/dev.db").replace("sqlite:///", "")
ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "changeme_secret_for_admin_pages")

app = Flask(__name__, template_folder="templates")

def db_connect():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def log_click(sim_id, user_agent=None, ip=None):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("INSERT INTO clicks (sim_id, user_agent, ip, ts) VALUES (?, ?, ?, ?)",
                (sim_id, user_agent, ip, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

@app.route("/")
def index():
    return "PhishBot landing app. Use /l/<sim_id> to view a simulation landing page."

@app.route("/l/<sim_id>")
def landing(sim_id):
    # Defensive: require sim_id to be known? For now, allow any sim_id but log it.
    # Capture metadata (do NOT store passwords)
    ip = request.remote_addr
    ua = request.headers.get("User-Agent", "")
    # Ensure clicks table exists (init_db.py will do so but safe guard)
    conn = db_connect()
    cur = conn.cursor()
    # create clicks table if not present
    cur.execute("""CREATE TABLE IF NOT EXISTS clicks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sim_id TEXT,
                    user_agent TEXT,
                    ip TEXT,
                    ts TEXT
                   )""")
    conn.commit()
    conn.close()

    # Log the click
    try:
        log_click(sim_id, user_agent=ua, ip=ip)
    except Exception as e:
        print("Failed to log click:", e)

    # Render educational landing page
    return render_template("landing.html", sim_id=sim_id)

@app.route("/admin", methods=["GET"])
def admin():
    # Basic admin summary (protected by a secret token param)
    token = request.args.get("token")
    if token != ADMIN_SECRET:
        abort(403)
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT sim_id, COUNT(*) as clicks FROM clicks GROUP BY sim_id ORDER BY clicks DESC")
    rows = cur.fetchall()
    conn.close()
    return render_template("base.html", rows=rows)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
