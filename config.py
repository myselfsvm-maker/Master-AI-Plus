import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Comma-separated list of OpenRouter API keys.
# Get free keys at https://openrouter.ai/keys (no credit card needed for :free models).
# Adding more than one key (e.g. from separate OpenRouter accounts) gives the bot
# more headroom before it has to fall back to a different model.
OPENROUTER_KEYS = [k.strip() for k in os.getenv("OPENROUTER_KEYS", "").split(",") if k.strip()]

# Friendly name -> OpenRouter model id, in fallback priority order.
# Models with a ":free" suffix cost $0 on OpenRouter (rate-limited, e.g. ~20-50 req/day).
# GPT-4 and Claude are NOT free anywhere - they're listed here so you can flip them on
# by adding OpenRouter credit later; until then they'll just be skipped automatically.
MODEL_CHAIN = [
    {"name": "gemini",   "model": "google/gemini-2.0-flash-exp:free"},
    {"name": "deepseek", "model": "deepseek/deepseek-chat:free"},
    {"name": "kimi",     "model": "moonshotai/kimi-k2:free"},
    {"name": "llama",    "model": "meta-llama/llama-3.3-70b-instruct:free"},
    {"name": "gpt4",     "model": "openai/gpt-4o"},           # paid - needs OpenRouter credit
    {"name": "claude",   "model": "anthropic/claude-3.5-sonnet"},  # paid - needs OpenRouter credit
]

MODEL_BY_NAME = {m["name"]: m["model"] for m in MODEL_CHAIN}

HISTORY_LIMIT = 20          # messages of context kept per user
COOLDOWN_SECONDS = 6 * 60 * 60  # how long to skip a key/model combo after it's rate-limited
