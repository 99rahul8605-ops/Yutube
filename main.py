import os
import re
import json
import logging
import asyncio
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import BadRequest
import yt_dlp
import requests
import aiohttp
import urllib.parse
from config import Config

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ensure directories exist
Path(Config.DOWNLOAD_PATH).mkdir(exist_ok=True)
Path("cookies").mkdir(exist_ok=True)

class YouTubeDownloaderBot:
    def __init__(self):
        self.downloading_users = set()
        # Try to load cookies on startup
        asyncio.create_task(self.load_cookies_on_startup())
        
    async def load_cookies_on_startup(self):
        """Load cookies from COOKIE_URL on startup"""
        if Config.COOKIE_URL:
            try:
                await self.download_cookies_from_url(Config.COOKIE_URL)
                logger.info("Successfully loaded cookies from COOKIE_URL on startup")
            except Exception as e:
                logger.error(f"Failed to load cookies on startup: {e}")
        else:
            logger.warning("COOKIE_URL not set, cookies will not be loaded automatically")
    
    async def download_cookies_from_url(self, url: str) -> bool:
        """Download cookies from a URL"""
        try:
            # Convert regular batbin URL to raw URL
            if "batbin.me/" in url and "/raw/" not in url:
                url = url.replace("batbin.me/", "batbin.me/raw/")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        cookies_content = await response.text()
                        
                        # Save to file
                        with open(Config.COOKIES_FILE, 'w') as f:
                            f.write(cookies_content)
                        
                        logger.info(f"Successfully downloaded cookies from {url}")
                        return True
                    else:
                        logger.error(f"Failed to fetch cookies. Status: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Error downloading cookies: {e}")
            return False
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send welcome message"""
        user = update.effective_user
        welcome_text = f"""
🤖 *YouTube Video Downloader Bot* 🤖

Hello {user.first_name}! I can download videos from YouTube and other platforms.

📌 *Available Commands:*
/start - Show this message
/download [url] - Download video
/settings - Configure download settings
/resolution [360|480|720|1080] - Set video quality
/status - Check bot status

🔧 *Admin Commands:*
/cookies - Upload cookies.txt file
/update_cookies - Update cookies from COOKIE_URL

⚠️ *Note:* Maximum file size: {Config.MAX_VIDEO_SIZE}MB
        """
        
        keyboard = [
            [
                InlineKeyboardButton("📥 Download Video", callback_data="download"),
                InlineKeyboardButton("⚙️ Settings", callback_data="settings")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle direct YouTube URLs"""
        if update.message.text and ("youtube.com" in update.message.text or "youtu.be" in update.message.text):
            await self.process_download(update, context, update.message.text)
    
    async def download_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /download command"""
        if not context.args:
            await update.message.reply_text("❌ Please provide a YouTube URL.\nUsage: /download https://youtube.com/watch?v=...")
            return
        
        url = context.args[0]
        await self.process_download(update, context, url)
    
    async def process_download(self, update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
        """Process video download"""
        user_id = update.effective_user.id
        
        # Check if user already downloading
        if user_id in self.downloading_users:
            await update.message.reply_text("⏳ You already have a download in progress. Please wait.")
            return
        
        # Validate URL
        if not self.validate_youtube_url(url):
            await update.message.reply_text("❌ Invalid YouTube URL. Please provide a valid YouTube link.")
            return
        
        try:
            self.downloading_users.add(user_id)
            message = await update.message.reply_text("🔍 Fetching video information...")
            
            # Get video info
            video_info = await self.get_video_info(url)
            if not video_info:
                await message.edit_text("❌ Failed to fetch video information.")
                return
            
            # Check video size
            if video_info.get('filesize', 0) > Config.MAX_VIDEO_SIZE * 1024 * 1024:
                await message.edit_text(f"❌ Video is too large (max {Config.MAX_VIDEO_SIZE}MB)")
                return
            
            # Ask for quality
            keyboard = []
            formats = video_info.get('formats', [])
            unique_resolutions = set()
            
            for fmt in formats:
                if fmt.get('height') and fmt.get('ext') in ['mp4', 'webm']:
                    resolution = f"{fmt['height']}p"
                    if resolution not in unique_resolutions:
                        unique_resolutions.add(resolution)
                        keyboard.append([
                            InlineKeyboardButton(f"📹 {resolution}", 
                            callback_data=f"dl_{self.encode_url(url)}_{fmt['height']}")
                        ])
            
            # Add audio only option
            keyboard.append([
                InlineKeyboardButton("🎵 Audio Only", callback_data=f"dl_{self.encode_url(url)}_audio")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            title = video_info.get('title', 'Unknown Video')[:50]
            await message.edit_text(
                f"📹 *{title}*\n\nSelect download quality:",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error processing download: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
        finally:
            self.downloading_users.discard(user_id)
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "download":
            await query.edit_message_text("📥 Send me a YouTube URL to download")
        
        elif data == "settings":
            await self.show_settings(query)
        
        elif data.startswith("dl_"):
            parts = data.split("_")
            if len(parts) >= 3:
                encoded_url = "_".join(parts[1:-1])
                url = self.decode_url(encoded_url)
                quality = parts[-1]
                await self.perform_download(query, url, quality)
            elif len(parts) == 2 and parts[1] == "audio":
                encoded_url = data[3:]  # Remove "dl_"
                url = self.decode_url(encoded_url)
                await self.perform_download(query, url, "audio")
    
    def encode_url(self, url: str) -> str:
        """Encode URL for callback data"""
        return urllib.parse.quote(url, safe='')
    
    def decode_url(self, encoded_url: str) -> str:
        """Decode URL from callback data"""
        return urllib.parse.unquote(encoded_url)
    
    async def perform_download(self, query, url: str, quality: str):
        """Perform the actual download"""
        user_id = query.from_user.id
        
        try:
            await query.edit_message_text("⏬ Downloading video...")
            
            # Prepare yt-dlp options
            ydl_opts = {
                'format': 'bestaudio/best' if quality == 'audio' else f'best[height<={quality[:-1]}]',
                'outtmpl': f'{Config.DOWNLOAD_PATH}/%(title)s.%(ext)s',
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'cookiefile': Config.COOKIES_FILE if os.path.exists(Config.COOKIES_FILE) else None,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Get info first
                info = ydl.extract_info(url, download=False)
                filename = ydl.prepare_filename(info)
                
                # Download
                ydl.download([url])
            
            # Send file
            await self.send_video(query, filename, quality)
            
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            if "Sign in to confirm" in error_msg or "cookies" in error_msg.lower():
                await query.edit_message_text(
                    "🔒 This video requires authentication.\n"
                    "Cookies need to be configured via COOKIE_URL environment variable."
                )
            else:
                await query.edit_message_text(f"❌ Download error: {error_msg[:100]}")
        except Exception as e:
            logger.error(f"Download error: {e}")
            await query.edit_message_text(f"❌ Error: {str(e)[:100]}")
    
    async def send_video(self, query, filepath: str, quality: str):
        """Send downloaded video to user"""
        try:
            file_size = os.path.getsize(filepath) / (1024 * 1024)  # MB
            
            if file_size > 50:  # Telegram file size limit
                # Compress if too large
                await query.edit_message_text("📦 File is large, compressing...")
                compressed_path = await self.compress_video(filepath)
                file_to_send = compressed_path
            else:
                file_to_send = filepath
            
            # Send file
            with open(file_to_send, 'rb') as video_file:
                if quality == 'audio':
                    await query.message.reply_audio(
                        audio=video_file,
                        caption="✅ Audio downloaded successfully!"
                    )
                else:
                    await query.message.reply_video(
                        video=video_file,
                        caption=f"✅ Video downloaded in {quality} quality!"
                    )
            
            await query.edit_message_text("✅ Download complete!")
            
            # Cleanup
            os.remove(filepath)
            if file_to_send != filepath and os.path.exists(file_to_send):
                os.remove(file_to_send)
                
        except BadRequest as e:
            if "file is too big" in str(e):
                await query.edit_message_text(
                    "❌ File is too large for Telegram.\n"
                    "Try downloading lower quality with /resolution command."
                )
            else:
                await query.edit_message_text(f"❌ Error sending file: {str(e)[:100]}")
        except Exception as e:
            logger.error(f"Error sending video: {e}")
            await query.edit_message_text(f"❌ Error: {str(e)[:100]}")
    
    async def compress_video(self, filepath: str) -> str:
        """Compress video using ffmpeg"""
        output_path = filepath.replace(".mp4", "_compressed.mp4")
        
        cmd = [
            'ffmpeg', '-i', filepath,
            '-vcodec', 'libx264',
            '-crf', '28',
            '-preset', 'fast',
            '-acodec', 'copy',
            output_path,
            '-y'
        ]
        
        process = await asyncio.create_subprocess_exec(*cmd)
        await process.wait()
        
        return output_path
    
    async def get_video_info(self, url: str) -> dict:
        """Get video information"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return None
    
    def validate_youtube_url(self, url: str) -> bool:
        """Validate YouTube URL"""
        patterns = [
            r'(https?://)?(www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
            r'(https?://)?(www\.)?youtu\.be/([a-zA-Z0-9_-]+)',
            r'(https?://)?(www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)',
            r'(https?://)?(www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]+)'
        ]
        
        for pattern in patterns:
            if re.match(pattern, url):
                return True
        return False
    
    async def show_settings(self, query):
        """Show settings menu"""
        cookies_status = "✅ Configured" if os.path.exists(Config.COOKIES_FILE) else "❌ Not configured"
        cookie_url_status = "✅ Set" if Config.COOKIE_URL else "❌ Not set"
        
        settings_text = f"""
⚙️ *Download Settings*

📏 Max File Size: {Config.MAX_VIDEO_SIZE}MB
🎬 Default Resolution: {Config.DEFAULT_RESOLUTION}p
🍪 Cookies: {cookies_status}
🔗 COOKIE_URL: {cookie_url_status}

Use /resolution to change default quality
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="settings")],
            [InlineKeyboardButton("⬅️ Back", callback_data="download")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(settings_text, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def resolution_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set download resolution"""
        if not context.args:
            resolutions = ["144", "240", "360", "480", "720", "1080"]
            keyboard = [[InlineKeyboardButton(f"{res}p", callback_data=f"set_res_{res}")] for res in resolutions]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "Select default download resolution:",
                reply_markup=reply_markup
            )
            return
        
        try:
            res = int(context.args[0])
            if res in [144, 240, 360, 480, 720, 1080]:
                Config.DEFAULT_RESOLUTION = str(res)
                await update.message.reply_text(f"✅ Default resolution set to {res}p")
            else:
                await update.message.reply_text("❌ Invalid resolution. Choose from: 144, 240, 360, 480, 720, 1080")
        except ValueError:
            await update.message.reply_text("❌ Please provide a valid number")
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle document upload (cookies.txt) - Local upload only"""
        user_id = update.effective_user.id
        
        if user_id not in Config.ADMIN_IDS:
            await update.message.reply_text("❌ Only admins can upload cookies.")
            return
        
        document = update.message.document
        if document.file_name != "cookies.txt":
            await update.message.reply_text("❌ Please upload a file named 'cookies.txt'")
            return
        
        try:
            # Download the file locally
            file = await document.get_file()
            await file.download_to_drive(Config.COOKIES_FILE)
            
            await update.message.reply_text(
                f"✅ Cookies uploaded successfully!\n"
                f"Note: This only updates local cookies. To persist, update COOKIE_URL environment variable."
            )
                
        except Exception as e:
            logger.error(f"Error handling cookies: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)[:100]}")
    
    async def update_cookies(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Update cookies from COOKIE_URL"""
        user_id = update.effective_user.id
        
        if user_id not in Config.ADMIN_IDS:
            await update.message.reply_text("❌ Only admins can update cookies.")
            return
        
        if not Config.COOKIE_URL:
            await update.message.reply_text("❌ COOKIE_URL environment variable not configured.")
            return
        
        try:
            success = await self.download_cookies_from_url(Config.COOKIE_URL)
            if success:
                await update.message.reply_text("✅ Cookies updated from COOKIE_URL!")
            else:
                await update.message.reply_text("❌ Failed to update cookies from COOKIE_URL")
                        
        except Exception as e:
            logger.error(f"Error updating cookies: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)[:100]}")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show bot status"""
        downloads_count = len(self.downloading_users)
        cookies_status = "✅ Configured" if os.path.exists(Config.COOKIES_FILE) else "❌ Not configured"
        cookie_url_status = "✅ Set" if Config.COOKIE_URL else "❌ Not set"
        
        status_text = f"""
📊 *Bot Status*

👥 Active Downloads: {downloads_count}
🍪 Local Cookies: {cookies_status}
🔗 COOKIE_URL: {cookie_url_status}
💾 Storage: {self.get_free_space()} free
        """
        
        await update.message.reply_text(status_text, parse_mode='Markdown')
    
    def get_free_space(self):
        """Get free disk space"""
        try:
            stat = os.statvfs(Config.DOWNLOAD_PATH)
            free = stat.f_bavail * stat.f_frsize / (1024 * 1024 * 1024)  # GB
            return f"{free:.1f}GB"
        except:
            return "Unknown"
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An error occurred. Please try again later."
            )

def main():
    """Start the bot"""
    if not Config.BOT_TOKEN:
        logger.error("BOT_TOKEN not set in environment variables")
        return
    
    # Create bot instance
    bot = YouTubeDownloaderBot()
    
    # Create application
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("download", bot.download_command))
    application.add_handler(CommandHandler("settings", bot.show_settings))
    application.add_handler(CommandHandler("resolution", bot.resolution_command))
    application.add_handler(CommandHandler("cookies", bot.handle_document))
    application.add_handler(CommandHandler("update_cookies", bot.update_cookies))
    application.add_handler(CommandHandler("status", bot.status_command))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    application.add_handler(MessageHandler(filters.Document.ALL, bot.handle_document))
    
    # Callback handler
    application.add_handler(CallbackQueryHandler(bot.handle_callback))
    
    # Error handler
    application.add_error_handler(bot.error_handler)
    
    # Start bot
    logger.info("Bot starting...")
    logger.info(f"COOKIE_URL configured: {bool(Config.COOKIE_URL)}")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()