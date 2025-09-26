#!/usr/bin/env python3
import os, sqlite3, io, csv
from datetime import datetime
from flask import Flask, request, render_template, redirect, url_for, abort, jsonify, send_file
from dotenv import load_dotenv

if os.path.exists("../.env"):
    load_dotenv("../.env")
else:
    load_dotenv()

DATABASE_PATH = os.environ.get("DATABASE_URL", "sqlite:///./db/dev.db").replace("sqlite:///", "")
ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "changeme_secret_for_admin_pages")

app = Flask(__name__, template_folder="templates")

def db_connect():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# helpers
def get_setting(k, default=None):
    conn = db_connect(); cur = conn.cursor()
    cur.execute("SELECT v FROM settings WHERE k = ?", (k,))
    r = cur.fetchone(); conn.close()
    return r['v'] if r else default

def set_setting(k, v):
    conn = db_connect(); cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO settings (k,v) VALUES (?,?)", (k, v))
    conn.commit(); conn.close()

@app.route("/")
def index():
    return "PhishBot Admin: go to /admin?token=YOUR_ADMIN_SECRET"

@app.route("/l/<sim_id>")
def landing(sim_id):
    user_id = request.args.get("u")
    ip = request.remote_addr
    ua = request.headers.get("User-Agent", "")
    # log click minimal (reuse clicks table)
    conn = db_connect(); cur = conn.cursor()
    cur.execute("INSERT INTO clicks (sim_id, user_id, user_agent, ip, ts) VALUES (?, ?, ?, ?, ?)",
                (sim_id, user_id, ua, ip, datetime.utcnow().isoformat()))
    conn.commit(); conn.close()
    return render_template("landing.html", sim_id=sim_id, user_id=user_id)

@app.route("/submit", methods=["POST"])
def submit():
    data = request.get_json(force=True, silent=True) or {}
    sim_id = data.get("sim_id")
    user_id = data.get("user_id")
    input_len = data.get("input_len")
    entropy = data.get("entropy")
    ip = request.remote_addr
    ua = request.headers.get("User-Agent", "")
    conn = db_connect(); cur = conn.cursor()
    cur.execute("""INSERT INTO clicks (sim_id, user_id, user_agent, ip, submitted, input_len, entropy_est, ts)
                   VALUES (?, ?, ?, ?, 1, ?, ?, ?)""",
                (sim_id, user_id, ua, ip, input_len, entropy, datetime.utcnow().isoformat()))
    conn.commit(); conn.close()
    return jsonify({"status":"ok","debrief":"This was a simulation. No real credentials were collected."})

# ADMIN UI
def require_token():
    token = request.args.get("token") or request.form.get("token")
    if token != ADMIN_SECRET:
        abort(403)

@app.route("/admin", methods=["GET"])
def admin():
    require_token()
    conn = db_connect(); cur = conn.cursor()
    # basic stats
    cur.execute("SELECT sim_id, COUNT(*) as clicks, SUM(submitted) as submissions FROM clicks GROUP BY sim_id ORDER BY clicks DESC")
    stats = cur.fetchall()
    # templates
    cur.execute("SELECT id, text, created_at FROM templates ORDER BY created_at DESC")
    templates = cur.fetchall()
    # settings
    labelled = get_setting("labelled_mode", "1")
    default_mode = get_setting("delivery_mode", "dm")
    return render_template("admin.html", rows=stats, templates=templates, labelled=int(labelled), default_mode=default_mode, token=ADMIN_SECRET)

@app.route("/admin/template", methods=["POST"])
def add_template():
    require_token()
    t_id = request.form.get("id").strip()
    text = request.form.get("text").strip()
    if not t_id or not text:
        return "Missing id or text", 400
    conn = db_connect(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO templates (id, text, created_at) VALUES (?, ?, ?)", (t_id, text, datetime.utcnow().isoformat()))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return "Template id exists", 400
    conn.close()
    return redirect(url_for("admin", token=ADMIN_SECRET))

@app.route("/admin/template/delete", methods=["POST"])
def delete_template():
    require_token()
    t_id = request.form.get("id")
    conn = db_connect(); cur = conn.cursor()
    cur.execute("DELETE FROM templates WHERE id = ?", (t_id,))
    conn.commit(); conn.close()
    return redirect(url_for("admin", token=ADMIN_SECRET))

@app.route("/admin/settings", methods=["POST"])
def update_settings():
    require_token()
    labelled = '1' if request.form.get("labelled") == "1" else '0'
    delivery = request.form.get("delivery", "dm")
    set_setting("labelled_mode", labelled)
    set_setting("delivery_mode", delivery)
    return redirect(url_for("admin", token=ADMIN_SECRET))

@app.route("/admin/campaign", methods=["POST"])
def create_campaign():
    require_token()
    name = request.form.get("name") or f"campaign_{datetime.utcnow().isoformat()}"
    mode = request.form.get("mode") or "dm"
    labelled = 1 if request.form.get("labelled") == "1" else 0
    template_id = request.form.get("template_id")
    created_by = request.form.get("created_by") or "web-admin"
    conn = db_connect(); cur = conn.cursor()
    cur.execute("""INSERT INTO campaigns (name, mode, labelled, template_id, created_by, created_at, status)
                   VALUES (?, ?, ?, ?, ?, ?, 'pending')""",
                (name, mode, labelled, template_id, created_by, datetime.utcnow().isoformat()))
    conn.commit(); conn.close()
    return redirect(url_for("admin", token=ADMIN_SECRET))

@app.route("/admin/export")
def admin_export():
    require_token()
    conn = db_connect(); cur = conn.cursor()
    cur.execute("SELECT id, sim_id, user_id, user_agent, ip, submitted, input_len, entropy_est, ts FROM clicks ORDER BY ts DESC")
    rows = cur.fetchall(); conn.close()
    output = io.StringIO(); writer = csv.writer(output)
    writer.writerow(["id","sim_id","user_id","user_agent","ip","submitted","input_len","entropy_est","ts"])
    for r in rows:
        writer.writerow([r["id"], r["sim_id"], r["user_id"], r["user_agent"], r["ip"], r["submitted"], r["input_len"], r["entropy_est"], r["ts"]])
    mem = io.BytesIO(); mem.write(output.getvalue().encode("utf-8")); mem.seek(0)
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="phish_clicks.csv")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
