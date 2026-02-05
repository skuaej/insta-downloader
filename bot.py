import os
import time
import requests
import logging
import psutil
import shutil

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ───────── CONFIG ─────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_URL = "https://underground-hildy-uhhy5-65dab051.koyeb.app/api/nuelink"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in environment variables")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ───────── HELPERS ─────────
def pretty_duration(d):
    try:
        parts = d.split(":")
        if len(parts) == 2:
            return f"{int(parts[0]):02d} min {int(parts[1]):02d} sec"
        if len(parts) == 3:
            return f"{int(parts[0])} hr {int(parts[1]):02d} min {int(parts[2]):02d} sec"
    except:
        pass
    return d

# ───────── /start ─────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 *Instagram Reel Stream Bot*\n\n"
        "Send an Instagram reel link and get:\n"
        "• Thumbnail\n"
        "• Duration\n"
        "• Direct stream link\n\n"
        "📊 /stats – bot status",
        parse_mode="Markdown"
    )

# ───────── /stats ─────────
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    ping = int((time.time() - start_time) * 1000)

    mem = psutil.virtual_memory()
    disk = shutil.disk_usage("/")

    await update.message.reply_text(
        "📊 *Bot Stats*\n\n"
        f"🏓 Ping: `{ping} ms`\n"
        f"🧠 RAM: `{mem.used // (1024**2)} / {mem.total // (1024**2)} MB`\n"
        f"💾 Disk: `{disk.used // (1024**2)} / {disk.total // (1024**2)} MB`\n"
        "⚡ Mode: Stream only",
        parse_mode="Markdown"
    )

# ───────── HANDLE LINK ─────────
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if "instagram.com" not in text:
        return

    await update.message.reply_text("🔍 Fetching reel info…")

    try:
        r = requests.get(API_URL, params={"url": text}, timeout=20)
        j = r.json()

        if not j.get("success"):
            raise Exception("API failed")

        d = j["data"]

        title = d.get("title", "Instagram Reel")
        uploader = d.get("uploader", "Unknown")
        thumb = d.get("thumbnail")
        stream = d.get("url")
        duration = pretty_duration(d.get("duration", "N/A"))

        caption = (
            "🎥 *Instagram Reel*\n\n"
            f"👤 *Uploader:* `{uploader}`\n"
            f"⏱ *Duration:* `{duration}`\n\n"
            "🔗 *Stream link:*\n"
            f"{stream}\n\n"
            "_No download. Direct streaming only._"
        )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Play Stream", url=stream)]
        ])

        await update.message.reply_photo(
            photo=thumb,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(e)
        await update.message.reply_text(
            "❌ Failed to fetch reel.\n"
            "Try again after some time."
        )

# ───────── MAIN ─────────
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

    logger.info("🤖 Bot started successfully")
    app.run_polling()

if __name__ == "__main__":
    main()
