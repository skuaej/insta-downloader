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
BOT_TOKEN = "PASTE_YOUR_REAL_BOT_TOKEN_HERE"
API_URL = "https://underground-hildy-uhhy5-65dab051.koyeb.app/api/nuelink"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────
# HELPERS
# ─────────────────────────────
def format_duration(duration: str) -> str:
    try:
        parts = duration.split(":")
        if len(parts) == 2:
            return f"{int(parts[0]):02d} min {int(parts[1]):02d} sec"
        if len(parts) == 3:
            return f"{int(parts[0])} hr {int(parts[1]):02d} min {int(parts[2]):02d} sec"
    except:
        pass
    return duration or "N/A"

# ─────────────────────────────
# /start
# ─────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 *Instagram Reel Stream Bot*\n\n"
        "Send any Instagram Reel link\n\n"
        "You’ll get:\n"
        "• Thumbnail\n"
        "• Duration\n"
        "• Direct Stream Link\n\n"
        "📊 Use /stats to check bot status",
        parse_mode="Markdown"
    )

# ─────────────────────────────
# /stats
# ─────────────────────────────
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    msg = await update.message.reply_text("📊 Checking stats…")

    ping = int((time.time() - start_time) * 1000)
    mem = psutil.virtual_memory()
    disk = shutil.disk_usage("/")

    await msg.edit_text(
        "📊 *Bot Stats*\n\n"
        f"🏓 Ping: `{ping} ms`\n"
        f"🧠 RAM: `{mem.used // (1024**2)} MB / {mem.total // (1024**2)} MB`\n"
        f"💾 Disk: `{disk.used // (1024**2)} MB / {disk.total // (1024**2)} MB`\n\n"
        "⚡ Mode: Stream only (no downloads)",
        parse_mode="Markdown"
    )

# ─────────────────────────────
# HANDLE INSTAGRAM LINK
# ─────────────────────────────
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if "instagram.com" not in text:
        return

    status = await update.message.reply_text("🔍 Fetching reel details…")

    try:
        data = None

        # retry logic
        for _ in range(3):
            r = requests.get(API_URL, params={"url": text}, timeout=20)
            data = r.json()
            if data.get("success"):
                break
            time.sleep(2)

        if not data or not data.get("success"):
            await status.edit_text("❌ API busy. Try again later 🙏")
            return

        info = data["data"]

        thumbnail = info.get("thumbnail")
        stream_url = info.get("url")
        uploader = info.get("uploader", "Unknown")
        duration = format_duration(info.get("duration", "N/A"))

        if not stream_url:
            raise Exception("Stream URL missing")

        caption = (
            "🎥 *Instagram Reel*\n\n"
            f"👤 *Uploader:* `{uploader}`\n"
            f"⏱ *Duration:* `{duration}`\n\n"
            "🔗 *Stream Link:*\n"
            f"{stream_url}\n\n"
            "_⚠ Stream only • No download_"
        )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Play Stream", url=stream_url)]
        ])

        await update.message.reply_photo(
            photo=thumbnail,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

        # safely delete status message
        try:
            await status.delete()
        except:
            pass

    except Exception as e:
        logger.error(e)
        try:
            await status.edit_text("❌ Failed to fetch reel. Try again later.")
        except:
            pass

# ─────────────────────────────
# MAIN
# ─────────────────────────────
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

    logger.info("Bot started successfully")
    app.run_polling()

if __name__ == "__main__":
    main()
