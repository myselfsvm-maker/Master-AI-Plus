import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

import config
import db
import key_manager
import providers

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "You are a helpful multi-model AI assistant running inside a Telegram bot. "
        "Answer clearly and concisely. Use proper Markdown code blocks for code."
    ),
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.ensure_user(update.effective_user.id)
    await update.message.reply_text(
        "Hey! I'm your multi-model AI assistant.\n\n"
        "I can draft content, help with code, and generate images - automatically "
        "switching between free-tier models (Gemini, DeepSeek, Kimi, Llama) when one "
        "runs low on quota, without losing our conversation.\n\n"
        "Commands:\n"
        "/model - see or switch the preferred model\n"
        "/newchat - clear conversation memory\n"
        "/status - see which model answered last\n"
        "/image <prompt> - generate an image\n\n"
        "Just type normally to chat!"
    )


async def model_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.ensure_user(user_id)
    names = [m["name"] for m in config.MODEL_CHAIN]
    args = context.args

    if not args:
        current = db.get_user_model(user_id)
        await update.message.reply_text(
            f"Current mode: {current}\n\n"
            f"Available: {', '.join(names)}, auto\n"
            f"Use /model <name> to switch. 'auto' lets me pick and fail over automatically."
        )
        return

    choice = args[0].lower()
    if choice != "auto" and choice not in names:
        await update.message.reply_text(f"Unknown model. Choose from: {', '.join(names)}, auto")
        return

    db.set_user_model(user_id, choice)
    await update.message.reply_text(f"Switched preferred model to: {choice}")


async def newchat_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.clear_history(update.effective_user.id)
    await update.message.reply_text("Conversation memory cleared. Starting fresh!")


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    last_model = db.get_last_model_used(update.effective_user.id) or "none yet"
    await update.message.reply_text(f"Last reply came from: {last_model}")


async def image_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("Usage: /image a red fox in a snowy forest")
        return
    await update.message.chat.send_action(ChatAction.UPLOAD_PHOTO)
    url = await providers.generate_image_url(prompt)
    await update.message.reply_photo(photo=url, caption=f"\U0001f5bc {prompt}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.ensure_user(user_id)
    text = update.message.text
    db.add_message(user_id, "user", text)

    preferred = db.get_user_model(user_id)
    history = db.get_history(user_id, limit=config.HISTORY_LIMIT)
    messages = [SYSTEM_PROMPT] + history

    await update.message.chat.send_action(ChatAction.TYPING)

    tried = set()
    reply_text = None
    used_model_name = None
    max_attempts = len(config.MODEL_CHAIN) * max(len(config.OPENROUTER_KEYS), 1)

    for _ in range(max_attempts):
        try:
            model_name, model_id, api_key = key_manager.get_next_backend(preferred, tried)
        except key_manager.NoAvailableBackend:
            break

        tried.add((model_name, api_key))
        try:
            reply_text = await providers.chat_completion(model_id, api_key, messages)
            used_model_name = model_name
            break
        except providers.QuotaError:
            log.warning("Quota hit for %s, rotating to next backend...", model_name)
            key_manager.mark_key_exhausted(model_id, api_key)
            continue
        except providers.ProviderError as e:
            log.warning("Provider error on %s: %s, rotating...", model_name, e)
            continue

    if reply_text is None:
        await update.message.reply_text(
            "All configured models are currently rate-limited. Please try again shortly, "
            "or add more OpenRouter API keys to OPENROUTER_KEYS in your .env file."
        )
        return

    db.add_message(user_id, "assistant", reply_text, model_used=used_model_name)
    await update.message.reply_text(f"{reply_text}\n\n— via {used_model_name}")


def build_application():
    """Builds (but does not run) the Telegram Application. Reused by main() below
    and by render_app.py, which runs it alongside a small health-check web server."""
    if not config.TELEGRAM_BOT_TOKEN:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in your .env file")
    if not config.OPENROUTER_KEYS:
        raise SystemExit("Set at least one key in OPENROUTER_KEYS in your .env file")

    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("model", model_cmd))
    app.add_handler(CommandHandler("newchat", newchat_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("image", image_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return app


def main():
    """Local / VPS entrypoint - simple blocking polling loop."""
    db.init_db()
    app = build_application()
    log.info("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
