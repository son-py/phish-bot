# PhishBot — Phishing Awareness Chatbot (Starter)

A consent-driven **Discord phishing simulation & awareness chatbot** with a Flask-based landing page and admin panel.  
Built for security training and awareness exercises, not for real phishing.

---

## ✨ Features
- 🤖 **Discord Bot**
  - `!optin` / `!optout` to manage consent.
  - Sends templated simulated phishing messages.
  - Educational chatbot commands:
    - `!tip` / `!tips` — random security awareness tips.
    - `!faq <topic>` — quick answers to common security questions.
    - `!quiz` — short awareness quiz.
    - `!phishcheck <text/link>` — basic heuristic risk check.
- 🌐 **Flask Web App**
  - Landing page for simulated phishing links.
  - Admin UI at `/admin?token=ADMIN_SECRET` with:
    - Manage settings
    - Manage templates
    - Launch campaigns
    - View click/submission stats
- 💾 **Database**
  - SQLite (dev by default), easy to swap for Postgres/MySQL.
  - Tracks campaigns, user consent, clicks.

---

## 🚀 Quickstart (local)

### 1. Clone repo & install deps
```bash
git clone https://github.com/son-py/phish-bot.git
cd phish-bot
python -m venv venv
.\venv\Scripts\activate   # Windows
pip install -r bot/requirements.txt
pip install -r web/requirements.txt
