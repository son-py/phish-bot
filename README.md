# PhishBot — Phishing Awareness Chatbot (Starter)

Short: A consent-driven Discord phishing simulation bot + Flask landing page for awareness training.

## Features
- Discord bot: opt-in (`!optin`) / opt-out (`!optout`) commands.
- Sends templated simulated phishing messages that link to an educational landing page.
- Click logging to a database (SQLite for dev).
- Admin summary page at `/admin?token=ADMIN_SECRET`.

## Quickstart (local)
1. Copy `.env.example` to `.env` and fill values.
2. Create a Discord bot and get its token. Set `DISCORD_TOKEN` and `TEST_CHANNEL_ID`.
3. Initialize DB:
   ```bash
   python db/init_db.py
