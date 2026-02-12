import logging
import requests
import json
import os
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

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
                    "⚠️ _High quality file detected. Use the button to download._",
                    reply_markup=reply_markup, parse_mode="Markdown"
                )
        else:
            await status_msg.edit_text("❌ **No working link found.**")
    except Exception as e:
        logger.error(f"Error: {e}")
        await status_msg.edit_text("⚠️ **API Error.**")

if __name__ == '__main__':
    if not TOKEN:
        print("ERROR: BOT_TOKEN variable not found in environment!")
        sys.exit(1)
        
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.run_polling()
