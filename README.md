# Multi-Model AI Aggregator — Telegram Bot

One Telegram bot that chats using Gemini, DeepSeek, Kimi, and Llama (all free) via
[OpenRouter](https://openrouter.ai) — one unified, OpenAI-compatible API. When your current
model/key hits its free daily quota, the bot automatically rotates to the next one **without
losing the conversation**, because chat history is stored in SQLite, not in memory.

GPT-4 and Claude are included in the fallback chain too, but they are **not free anywhere** —
they only activate if you add paid credit to your OpenRouter account. Until then the bot just
skips them automatically.

## How the auto-switching works

1. Every model in `config.py`'s `MODEL_CHAIN` is tried in order (or starting from your
   `/model` preference).
2. If a model/key combo returns a rate-limit or quota error, it's marked "exhausted" in
   the database with a cooldown, and the bot immediately retries with the next one.
3. Your full conversation history (from SQLite) is sent to whichever model answers, so
   context is never lost when the backend changes mid-conversation.
4. You can add multiple OpenRouter API keys (comma-separated) — e.g. from a couple of free
   OpenRouter accounts — so you have more daily requests before any fallback is needed.

## 1. Get your credentials

- **Telegram bot token**: message [@BotFather](https://t.me/BotFather) on Telegram, run
  `/newbot`, and copy the token it gives you.
- **OpenRouter API key(s)**: sign up free at https://openrouter.ai/keys — no credit card
  needed to use `:free` models. You can create more than one account for extra daily quota
  if you like, and add all the keys to `OPENROUTER_KEYS` comma-separated.

## 2. Local setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and fill in TELEGRAM_BOT_TOKEN and OPENROUTER_KEYS
python bot.py
```

Message your bot on Telegram — it should respond immediately.

## 3. Deploy on Render.com (free option)

Render's free tier only applies to **Web Services** (things that respond to HTTP), not
Background Workers (those start at $7/mo). Since this bot just polls Telegram, `render_app.py`
adds a tiny health-check web server alongside it so Render's free tier accepts it as a Web
Service.

**Steps:**
1. Push this folder to a GitHub repository.
2. On [render.com](https://render.com), click **New +** → **Web Service**, connect your repo.
3. Set:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python render_app.py`
   - **Instance Type**: Free
4. Under **Environment**, add:
   - `TELEGRAM_BOT_TOKEN` = your token
   - `OPENROUTER_KEYS` = your key(s)
5. Click **Deploy**. Once live, message your bot on Telegram to test it.

**The catch with free Web Services:** Render spins them down after 15 minutes with no HTTP
traffic, which would kill the bot's connection. Fix it for free with an uptime pinger:
- Sign up free at [uptimerobot.com](https://uptimerobot.com)
- Add a new HTTP(s) monitor pointed at your Render URL (shown on your service's dashboard),
  checking every 5 minutes.
- This keeps the health endpoint "warm" so Render never spins the service down.

This combo (free Web Service + free uptime pinger) costs $0 but has a small risk of brief
gaps. If you want guaranteed 24/7 uptime with no workarounds, upgrade that one service to
Render's **Starter** plan (~$7/mo) — no code changes needed, just flip the instance type.

## 4. Deploy on a VPS (24/7, paid but simple)

Copy the folder to your server, repeat the setup above, then run it as a systemd service
so it survives reboots and restarts on crash:

```ini
# /etc/systemd/system/ai-bot.service
[Unit]
Description=Multi-Model AI Telegram Bot
After=network.target

[Service]
Type=simple
User=YOUR_LINUX_USER
WorkingDirectory=/path/to/ai-aggregator-bot
ExecStart=/path/to/ai-aggregator-bot/venv/bin/python bot.py
Restart=always
RestartSec=5
EnvironmentFile=/path/to/ai-aggregator-bot/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ai-bot
sudo systemctl status ai-bot
journalctl -u ai-bot -f   # tail logs
```

## Commands

| Command | What it does |
|---|---|
| `/start` | Intro message |
| `/model` | Show or switch preferred model (`gemini`, `deepseek`, `kimi`, `llama`, `gpt4`, `claude`, or `auto`) |
| `/newchat` | Clear conversation memory |
| `/status` | Show which model answered your last message |
| `/image <prompt>` | Generate an image (free, via Pollinations.ai, no key needed) |

## Extending it

- **Add a real Google Gemini key instead of OpenRouter's Gemini**: Google AI Studio gives a
  separate, generous free tier (https://aistudio.google.com/apikey). You'd add a small
  provider function in `providers.py` and a matching entry in `config.MODEL_CHAIN`.
- **Add native DeepSeek or Moonshot (Kimi) keys**: both have their own OpenAI-compatible
  endpoints; same pattern as above.
- **Per-provider paid keys with rotation**: the `key_manager.py` design already supports
  multiple keys per model — just add more entries to `OPENROUTER_KEYS`, or extend
  `MODEL_CHAIN`/`config` to hold separate key lists per provider if you move off OpenRouter.

## Honest limitations

- Free-tier models on OpenRouter have daily/per-minute rate limits set by OpenRouter and the
  underlying labs, not by this bot — once every key/model in your chain is on cooldown, the
  bot tells the user to wait rather than failing silently.
- This bot rotates between **API keys and accounts you legitimately own and control**. It
  does not, and should not be extended to, automatically create new accounts/emails to keep
  exploiting free trials — that breaks the terms of service of every provider involved and
  will get keys/IPs banned.
- Image generation uses Pollinations.ai's free public endpoint; quality is decent but not on
  par with paid models like DALL-E 3 or Midjourney.
