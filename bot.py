import logging
import requests
import os
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# Heroku Environment Variable se Token uthayega
TOKEN = os.environ.get("BOT_TOKEN")
API_URL = "https://instaaaa-pi.vercel.app/download"

# Standard Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# --- START COMMAND HANDLER ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    welcome_text = (
        f"Hey **{user_name}**! Welcome to the **Universal Downloader Bot** 🚀\n\n"
        "I can download media from almost everywhere! Just send me a link from:\n"
        "📺 **YouTube**\n"
        "📸 **Instagram**\n"
        "🎵 **TikTok**\n"
        "🎧 **Spotify**\n"
        "👥 **Facebook**\n\n"
        "✨ _Just paste the link below and I'll do the rest!_"
    )
    
    # Optional: Ek button bhi daal dete hain for style
    keyboard = [[InlineKeyboardButton("Developer 🛠️", url="https://t.me/your_username")]] # Replace with your TG link
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")
    logger.info(f"User {user_name} started the bot.")

def get_media_data(data):
    results = data.get("all_results") or data.get("results", {})
    metadata = {
        "link": data.get("clean_download_url"),
        "title": "Universal Media",
        "desc": "Downloaded via Universal Bot",
        "platform": data.get("platform", "Media").capitalize(),
        "type": "video"
    }

    for provider, content in results.items():
        if isinstance(content, dict) and content.get("status") != "failed":
            if content.get("title"): metadata["title"] = content["title"]
            if content.get("author"): metadata["desc"] = f"By: {content['author']}"
            
            keys = ["no_watermark", "no_watermark_hd", "video_url", "download_url", "url", "mp3"]
            for key in keys:
                link = content.get(key)
                if link and isinstance(link, str) and link.startswith("http"):
                    if "token=" in link and len(link) < 60: continue
                    if any(x in link.lower() for x in [".jpg", ".png", ".webp"]): continue
                    metadata["link"] = link
                    if key == "mp3" or "spotify" in data.get("platform", "").lower():
                        metadata["type"] = "audio"
                    return metadata
    return metadata if metadata["link"] else None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if not url.startswith("http"): return

    logger.info(f"Processing URL: {url}")
    status_msg = await update.message.reply_text("🔎 **Searching for your media...**", parse_mode="Markdown")

    try:
        response = requests.get(f"{API_URL}?url={url}", timeout=25)
        data = response.json()
        media = get_media_data(data)

        if media and media["link"]:
            title = media['title'][:100]
            caption = f"🎬 **{title}**\n👤 {media['desc']}\n\n✨ _Powered by Universal Bot_"
            
            try:
                if media["type"] == "audio":
                    await update.message.reply_audio(audio=media["link"], caption=caption, parse_mode="Markdown")
                else:
                    await update.message.reply_video(video=media["link"], caption=caption, parse_mode="Markdown", supports_streaming=True)
                await status_msg.delete()
            except Exception:
                keyboard = [[InlineKeyboardButton("📥 Download File", url=media['link'])]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await status_msg.edit_text(
                    f"📦 **File Found on {media['platform']}**\n\n🎬 **Title:** {title}\n\n"
                    "⚠️ _The file is too large for direct Telegram upload. Use the button below._",
                    reply_markup=reply_markup, parse_mode="Markdown"
                )
        else:
            await status_msg.edit_text("❌ **Sorry, I couldn't find any working link.**")
    except Exception as e:
        logger.error(f"Error: {e}")
        await status_msg.edit_text("⚠️ **API Error.**")

if __name__ == '__main__':
    if not TOKEN:
        logger.error("BOT_TOKEN not found in environment!")
        sys.exit(1)
        
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start)) # Start button logic
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    logger.info("Universal Bot with Start Button is Running...")
    app.run_polling()
