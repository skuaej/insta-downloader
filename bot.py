import os
import time
import requests
import logging
import psutil
import shutil
import html  # <--- Added this to handle special characters safely

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

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ───────── HELPERS ─────────
def pretty_duration(d):
    try:
        parts = str(d).split(":")
        if len(parts) == 2:
            return f"{int(parts[0]):02d} min {int(parts[1]):02d} sec"
        if len(parts) == 3:
            return f"{int(parts[0])} hr {int(parts[1]):02d} min {int(parts[2]):02d} sec"
    except:
        pass
    return str(d)

# ───────── /start ─────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 <b>Instagram Reel Stream Bot</b>\n\n"
        "Send an Instagram reel link and get:\n"
        "• Thumbnail\n"
        "• Duration\n"
        "• Direct stream link\n\n"
        "📊 /stats – bot status",
        parse_mode="HTML"
    )

# ───────── /stats ─────────
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    ping = int((time.time() - start_time) * 1000)

    mem = psutil.virtual_memory()
    disk = shutil.disk_usage("/")

    await update.message.reply_text(
        "📊 <b>Bot Stats</b>\n\n"
        f"🏓 Ping: <code>{ping} ms</code>\n"
        f"🧠 RAM: <code>{mem.used // (1024**2)} / {mem.total // (1024**2)} MB</code>\n"
        f"💾 Disk: <code>{disk.used // (1024**2)} / {disk.total // (1024**2)} MB</code>\n"
        "⚡ Mode: Stream only",
        parse_mode="HTML"
    )

# ───────── HANDLE LINK ─────────
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if "instagram.com" not in text:
        return

    # Send a temporary message to show activity
    status_msg = await update.message.reply_text("🔍 Fetching reel info…")

    try:
        # Request with headers to mimic a browser (avoids some bot blocks)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        r = requests.get(API_URL, params={"url": text}, headers=headers, timeout=20)
        j = r.json()

        if not j.get("success"):
            raise Exception("API returned false success")

        d = j.get("data", {})

        # -- SAFE DATA HANDLING --
        # We must escape special characters (<, >, &) for HTML parsing
        title = html.escape(d.get("title", "Instagram Reel"))
        uploader = html.escape(d.get("uploader", "Unknown"))
        stream_url = d.get("url")
        thumb = d.get("thumbnail")
        duration = pretty_duration(d.get("duration", "N/A"))

        if not stream_url:
            raise Exception("No URL found in API response")

        # HTML Caption
        caption = (
            f"🎥 <b>Instagram Reel</b>\n\n"
            f"👤 <b>Uploader:</b> <code>{uploader}</code>\n"
            f"⏱ <b>Duration:</b> <code>{duration}</code>\n\n"
            f"🔗 <b>Stream link:</b>\n"
            f"<a href='{stream_url}'>Click Here to Watch</a>\n\n"
            f"<i>No download. Direct streaming only.</i>"
        )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Play Stream", url=stream_url)]
        ])

        # Delete status message
        await status_msg.delete()

        # Send the result
        await update.message.reply_photo(
            photo=thumb,
            caption=caption,
            parse_mode="HTML", # Changed from Markdown to HTML
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f"Error: {e}")
        # Edit the status message to show error
        try:
            await status_msg.edit_text(
                "❌ <b>Failed to fetch reel.</b>\n"
                "The API might be busy or the link is private.",
                parse_mode="HTML"
            )
        except:
            pass
            
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
