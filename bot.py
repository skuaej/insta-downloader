import time
import requests
import psutil
import shutil
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = "YOUR_BOT_TOKEN"
API_URL = "https://underground-hildy-uhhy5-65dab051.koyeb.app/api/nuelink"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────
# Helpers
# ─────────────────────────────
def format_duration(duration_str: str) -> str:
    """
    Converts '1:27' → '01 min 27 sec'
    """
    try:
        parts = duration_str.split(":")
        if len(parts) == 2:
            return f"{int(parts[0]):02d} min {int(parts[1]):02d} sec"
        if len(parts) == 3:
            return f"{int(parts[0])} hr {int(parts[1]):02d} min {int(parts[2]):02d} sec"
    except:
        pass
    return duration_str

# ─────────────────────────────
# /start
# ─────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 **Instagram Reel Stream Bot**\n\n"
        "Send any Instagram reel link\n"
        "You’ll get:\n"
        "• Thumbnail\n"
        "• Video length\n"
        "• Direct stream link\n\n"
        "📊 /stats – bot status",
        parse_mode="Markdown"
    )

# ─────────────────────────────
# /stats
# ─────────────────────────────
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_t = time.time()
    msg = await update.message.reply_text("Checking bot stats…")

    ping = int((time.time() - start_t) * 1000)
    mem = psutil.virtual_memory()
    disk = shutil.disk_usage("/")

    await msg.edit_text(
        "📊 **Bot Stats**\n\n"
        f"🏓 Ping: `{ping} ms`\n"
        f"🧠 RAM: `{mem.used // (1024**2)} MB / {mem.total // (1024**2)} MB`\n"
        f"💾 Disk: `{disk.used // (1024**2)} MB / {disk.total // (1024**2)} MB`\n"
        "⚡ Mode: Stream only (no download)",
        parse_mode="Markdown"
    )

# ─────────────────────────────
# Handle Instagram link
# ─────────────────────────────
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if "instagram.com" not in text:
        return

    status = await update.message.reply_text("🔍 Fetching reel details…")

    try:
        r = requests.get(API_URL, params={"url": text}, timeout=15)
        data = r.json()

        if not data.get("success"):
            raise Exception("API failed")

        info = data["data"]

        title = info.get("title", "Instagram Reel")
        thumb = info.get("thumbnail")
        stream_url = info.get("url")
        uploader = info.get("uploader", "Unknown")
        duration = format_duration(info.get("duration", "N/A"))

        caption = (
            "🎥 **Instagram Reel**\n\n"
            f"👤 **Uploader:** `{uploader}`\n"
            f"⏱ **Duration:** `{duration}`\n\n"
            "🔗 **Stream Link:**\n"
            f"{stream_url}\n\n"
            "_⚠ No download. Direct streaming only._"
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
            "😅 Server is under heavy load.\n"
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
