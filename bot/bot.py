#!/usr/bin/env python3
"""
Simple Discord bot that sends consented simulated "phishing" messages
which point to a safe landing page hosted by the Flask app.

IMPORTANT:
- Only message users/channels that have explicitly opted in.
- Never collect real credentials.
"""

import os
import json
import random
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
import discord
from discord.ext import commands, tasks

load_dotenv("../.env") if os.path.exists("../.env") else load_dotenv()

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
TEST_CHANNEL_ID = int(os.environ.get("TEST_CHANNEL_ID", "0"))
WEB_BASE_URL = os.environ.get("WEB_BASE_URL", "http://localhost:8000")
DATABASE_PATH = os.environ.get("DATABASE_URL", "sqlite:///./db/dev.db").replace("sqlite:///", "")

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Load templates
with open("templates.json", "r", encoding="utf-8") as f:
    TEMPLATES = json.load(f)['phish']

def db_connect():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def ensure_tables():
    conn = db_connect()
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
    conn.commit()
    conn.close()

@bot.event
async def on_ready():
    ensure_tables()
    print(f"Bot connected as {bot.user}.")
    send_simulations.start()

@bot.command(name="optin")
async def optin(ctx):
    """User opts in to receive simulations."""
    discord_id = str(ctx.author.id)
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO users (discord_id, consent, opted_out, ts) VALUES (?, ?, ?, ?)",
                (discord_id, 1, 0, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    await ctx.send("✅ You are now opted in for phishing awareness simulations. You can opt out anytime with !optout")

@bot.command(name="optout")
async def optout(ctx):
    """User opts out."""
    discord_id = str(ctx.author.id)
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("UPDATE users SET opted_out=1, consent=0 WHERE discord_id = ?", (discord_id,))
    conn.commit()
    conn.close()
    await ctx.send("✅ You have been opted out. You will no longer receive simulated messages.")

@bot.command(name="status")
async def status(ctx):
    discord_id = str(ctx.author.id)
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT consent, opted_out FROM users WHERE discord_id = ?", (discord_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        await ctx.send(f"Consent: {row['consent']}, Opted out: {row['opted_out']}")
    else:
        await ctx.send("You have not opted in. Use !optin to opt in.")

@tasks.loop(minutes=5)  # For testing, runs every 5 minutes. Change to hours/days for production.
async def send_simulations():
    """
    Picks one template and sends it to the test channel (or DMs) for users that consented.
    NOTE: This example sends to a configured test channel. Use DMs carefully and only with consent.
    """
    if TEST_CHANNEL_ID == 0:
        return
    try:
        channel = bot.get_channel(TEST_CHANNEL_ID) or await bot.fetch_channel(TEST_CHANNEL_ID)
    except Exception as e:
        print("Could not fetch test channel:", e)
        return

    # Get users who consented and are not opted out
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT discord_id FROM users WHERE consent=1 AND opted_out=0")
    rows = cur.fetchall()
    conn.close()
    if not rows:
        # nothing to send
        return

    # For demo: send one message to the test channel (can be per-user DM in real usage)
    tmpl = random.choice(TEMPLATES)
    sim_id = tmpl['id']
    link = f"{WEB_BASE_URL}/l/{sim_id}"
    # basic personalization
    message = tmpl['text'].replace("{{link}}", link).replace("{{name}}", "friend")

    # send to channel
    await channel.send(f"**Simulated Message**\n{message}\n\n*(This is a simulated phishing message for consenting users only.)*")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("ERROR: DISCORD_TOKEN not set in environment.")
        exit(1)
    ensure_tables()
    bot.run(DISCORD_TOKEN)
