import os
import logging
import httpx
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters
)

# ─── ENV CONFIG ──────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
VERCEL_API_URL = os.getenv("VERCEL_API_URL")

if not BOT_TOKEN or not VERCEL_API_URL:
    raise RuntimeError("Missing BOT_TOKEN or VERCEL_API_URL")

# ─── LOGGING ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me a Reel link!")

async def handle_instagram_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    chat_id = update.effective_chat.id

    if "instagram.com" not in user_message:
        await update.message.reply_text("⚠️ That doesn't look like an Instagram link.")
        return

    # 1. INITIAL STATUS
    status_msg = await update.message.reply_text("🔄 Connecting to server...")

    payload = {"url": user_message}
    video_url = None
    
    # Using a shared client for better performance
    async with httpx.AsyncClient(timeout=45.0) as client:
        
        # ─── STEP 1: GET LINK FROM API (WITH RETRY) ──────────────────────────
        for attempt in range(1, 4):
            try:
                response = await client.post(VERCEL_API_URL, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    video_url = data.get("download_url")
                    if video_url:
                        break # Success! Exit loop
                    else:
                        await status_msg.edit_text("❌ API returned no URL.")
                        return
                
                elif response.status_code in [502, 503, 504]:
                    await status_msg.edit_text(f"⏳ Server busy ({response.status_code}). Retrying {attempt}/3...")
                    continue # Try again
                
                else:
                    await status_msg.edit_text(f"❌ API Error: {response.status_code}")
                    return

            except httpx.TimeoutException:
                if attempt == 3:
                    await status_msg.edit_text("❌ Server timed out. Try again later.")
                    return
                await status_msg.edit_text(f"⏳ Connection slow... Retrying {attempt}/3")
            
            except Exception as e:
                logging.error(f"Error: {e}")
                await status_msg.edit_text("❌ Connection failed.")
                return

        if not video_url:
            await status_msg.edit_text("❌ Failed to get video link after 3 tries.")
            return

        # ─── STEP 2: DOWNLOAD & UPLOAD ───────────────────────────────────────
        try:
            await status_msg.edit_text("⬇️ Downloading video...")
            
            # Download the video file to memory
            video_response = await client.get(video_url)
            
            if video_response.status_code == 200:
                await status_msg.edit_text("📤 Uploading...")
                
                # Send the binary content
                await update.message.reply_video(
                    video=video_response.content,
                    caption="Here is your video! 📥"
                )
                
                # Success - Delete status message
                await context.bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)
            else:
                await status_msg.edit_text(f"❌ Could not download video file (Status {video_response.status_code})")

        except Exception as e:
            logging.error(f"Upload failed: {e}")
            await status_msg.edit_text("❌ Failed to upload video (File might be too big).")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_instagram_link))
    
    print("🤖 Bot is running...")
    app.run_polling()
