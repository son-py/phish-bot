#!/usr/bin/env python3
import os, sqlite3, json, random, time
from datetime import datetime
from dotenv import load_dotenv
import discord
from discord.ext import commands, tasks

# load .env
if os.path.exists("../.env"):
    load_dotenv("../.env")
else:
    load_dotenv()

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
TEST_CHANNEL_ID = int(os.environ.get("TEST_CHANNEL_ID", "0"))
WEB_BASE_URL = os.environ.get("WEB_BASE_URL", "http://localhost:8000")
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./db/dev.db").replace("sqlite:///", "")
ADMIN_NOTIFY_CHANNEL = int(os.environ.get("ADMIN_NOTIFY_CHANNEL", "0"))

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def db_connect():
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn

def fetch_templates():
    conn = db_connect(); cur = conn.cursor()
    cur.execute("SELECT id, text FROM templates")
    rows = cur.fetchall(); conn.close()
    return rows

def fetch_opted_in_users():
    conn = db_connect(); cur = conn.cursor()
    cur.execute("SELECT discord_id FROM users WHERE consent=1 AND opted_out=0")
    rows = cur.fetchall(); conn.close()
    return [r['discord_id'] for r in rows]

def fetch_pending_campaign():
    conn = db_connect(); cur = conn.cursor()
    cur.execute("SELECT * FROM campaigns WHERE status='pending' ORDER BY created_at LIMIT 1")
    r = cur.fetchone(); conn.close()
    return r

def mark_campaign_sent(campaign_id):
    conn = db_connect(); cur = conn.cursor()
    cur.execute("UPDATE campaigns SET status='sent', sent_at=? WHERE id=?", (datetime.utcnow().isoformat(), campaign_id))
    conn.commit(); conn.close()

@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user}")
    check_campaigns.start()

@bot.command(name="optin")
async def optin(ctx):
    discord_id = str(ctx.author.id)
    conn = db_connect(); cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO users (discord_id, consent, opted_out, ts) VALUES (?,1,0,?)",
                (discord_id, datetime.utcnow().isoformat()))
    conn.commit(); conn.close()
    await ctx.send("✅ You are now opted in for phishing awareness simulations. You can opt out anytime with !optout")

@bot.command(name="optout")
async def optout(ctx):
    discord_id = str(ctx.author.id)
    conn = db_connect(); cur = conn.cursor()
    cur.execute("UPDATE users SET opted_out=1, consent=0 WHERE discord_id = ?", (discord_id,))
    conn.commit(); conn.close()
    await ctx.send("✅ You have been opted out. You will no longer receive simulated messages.")

@tasks.loop(seconds=15)  # poll every 15s for admin-created campaigns
async def check_campaigns():
    c = fetch_pending_campaign()
    if not c:
        return
    # set status sending to avoid races
    conn = db_connect(); cur = conn.cursor()
    cur.execute("UPDATE campaigns SET status='sending' WHERE id=?", (c['id'],))
    conn.commit(); conn.close()

    template_id = c['template_id']
    conn = db_connect(); cur = conn.cursor()
    cur.execute("SELECT text FROM templates WHERE id=?", (template_id,))
    t = cur.fetchone()
    conn.close()
    if not t:
        print("Template not found for campaign", c['id'])
        # mark failed
        conn = db_connect(); cur = conn.cursor()
        cur.execute("UPDATE campaigns SET status='failed' WHERE id=?", (c['id'],))
        conn.commit(); conn.close()
        return

    text = t['text']
    labelled = bool(c['labelled'])
    mode = c['mode']  # 'dm' or 'channel'
    sim_id = c['id']  # use campaign id as sim_id

    sent_count = 0
    if mode == 'channel':
        # post one message to the configured test channel
        try:
            channel = bot.get_channel(TEST_CHANNEL_ID) or await bot.fetch_channel(TEST_CHANNEL_ID)
            link = f"{WEB_BASE_URL}/l/{sim_id}"
            message = text.replace("{{link}}", link).replace("{{name}}", "Team")
            if labelled:
                await channel.send(f"**Simulated Message**\n{message}\n\n*(This is a simulated phishing message for consenting users only.)*")
            else:
                await channel.send(message)
            sent_count = 1
        except Exception as e:
            print("Failed send to channel:", e)
    else:
        # DM each opted-in user
        users = fetch_opted_in_users()
        for discord_id in users:
            try:
                user = await bot.fetch_user(int(discord_id))
                link = f"{WEB_BASE_URL}/l/{sim_id}?u={discord_id}"
                message = text.replace("{{link}}", link).replace("{{name}}", user.name if user else "Colleague")
                if labelled:
                    await user.send(f"**Simulated Message**\n{message}\n\n*(This is a simulated phishing message for consenting users only.)*")
                else:
                    await user.send(message)
                sent_count += 1
            except Exception as e:
                print("Failed DM to", discord_id, e)

    # mark campaign as sent
    mark_campaign_sent(c['id'])
    print(f"Campaign {c['id']} sent to {sent_count} recipients.")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("ERROR: DISCORD_TOKEN not set in environment.")
        exit(1)
    bot.run(DISCORD_TOKEN)
