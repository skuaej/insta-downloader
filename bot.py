import os
import time
import requests
import psutil
import shutil
import logging

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ─────────────────────────────
# CONFIG
# ─────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")  # 🔐 from env
API_URL = "https://underground-hildy-uhhy5-65dab051.koyeb.app/api/nuelink"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env variable not set")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────
# Helpers
# ─────────────────────────────
def format_duration(d: str) -> str:
    try:
        p = d.split(":")
        if len(p) == 2:
            return f"{int(p[0]):02d} min {int(p[1]):02d} sec"
        if len(p) == 3:
            return f"{int(p[0])} hr {int(p[1]):02d} min {int(p[2]):02d} sec"
    except:
        pass
    return d

# ─────────────────────────────
# /start
# ─────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 *Instagram Reel Stream Bot*\n\n"
        "Send any Instagram reel link\n\n"
        "You will get:\n"
        "• Thumbnail\n"
        "• Duration\n"
        "• Stream link only\n\n"
        "📊 /stats – bot status",
        parse_mode="Markdown"
    )

# ─────────────────────────────
# /stats
# ─────────────────────────────
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = time.time()
    msg = await update.message.reply_text("Checking stats…")

    ping = int((time.time() - t) * 1000)
    mem = psutil.virtual_memory()
    disk = shutil.disk_usage("/")

    await msg.edit_text(
        "📊 *Bot Stats*\n\n"
        f"🏓 Ping: `{ping} ms`\n"
        f"🧠 RAM: `{mem.used//1024//1024} / {mem.total//1024//1024} MB`\n"
        f"💾 Disk: `{disk.used//1024//1024} / {disk.total//1024//1024} MB`\n"
        "⚡ Mode: Stream only",
        parse_mode="Markdown"
    )

# ─────────────────────────────
# Handle Reel Link
# ─────────────────────────────
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if "instagram.com" not in text:
        return

    status = await update.message.reply_text("🔍 Fetching reel…")

    try:
        data = None

        # 🔁 Retry logic (3 tries)
        for _ in range(3):
            r = requests.get(API_URL, params={"url": text}, timeout=15)
            data = r.json()
            if data.get("success"):
                break
            time.sleep(2)

        if not data or not data.get("success"):
            raise Exception("API overloaded")

        info = data["data"]

        thumb = info.get("thumbnail")
        stream_url = info.get("url")
        duration = format_duration(info.get("duration", "N/A"))
        uploader = info.get("uploader", "Unknown")

        # 🚫 Block download links
        if stream_url.endswith(".mp4"):
            raise Exception("Download link blocked")

        caption = (
            "🎥 *Instagram Reel*\n\n"
            f"👤 *Uploader:* `{uploader}`\n"
            f"⏱ *Duration:* `{duration}`\n\n"
            "🔗 *Stream Link:*\n"
            f"{stream_url}\n\n"
            "_No download • Stream only_"
        )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Play Stream", url=stream_url)]
        ])

        await status.delete()
        await update.message.reply_photo(
            photo=thumb,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(e)
        await status.edit_text(
            "😅 Server under heavy load.\n"
            "Please be patient and try again 🙏"
        )

# ─────────────────────────────
# Main
# ─────────────────────────────
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

    app.run_polling()

if __name__ == "__main__":
    main()
