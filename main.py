import os
import re
import json
import logging
import asyncio
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters, CallbackContext
from telegram.error import BadRequest
import yt_dlp
import requests
import aiohttp
import urllib.parse
from config import Config
import shutil

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
    def __init__(self, updater):
        self.updater = updater
        self.downloading_users = set()
        # Try to load cookies on startup
        self.load_cookies_on_startup()
    
    def load_cookies_on_startup(self):
        """Load cookies from COOKIE_URL on startup"""
        if Config.COOKIE_URL:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                success = loop.run_until_complete(self.download_cookies_from_url(Config.COOKIE_URL))
                if success:
                    logger.info("Successfully loaded cookies from COOKIE_URL on startup")
                else:
                    logger.error("Failed to load cookies on startup")
            except Exception as e:
                logger.error(f"Failed to load cookies on startup: {e}")
        else:
            logger.warning("COOKIE_URL not set, cookies will not be loaded automatically")
    
    async def download_cookies_from_url(self, url: str) -> bool:
        """Download cookies from a URL"""
        try:
            # Convert regular batbin URL to raw URL
            if "batbin.me/" in url:
                # Handle both formats
                if "/raw/" not in url:
                    url = url.replace("batbin.me/", "batbin.me/raw/")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        cookies_content = await response.text()
                        
                        # Validate cookies format
                        if "youtube.com" in cookies_content.lower() or "# http" in cookies_content.lower():
                            # Save to file
                            with open(Config.COOKIES_FILE, 'w', encoding='utf-8') as f:
                                f.write(cookies_content)
                            
                            logger.info(f"Successfully downloaded cookies from {url}")
                            return True
                        else:
                            logger.error("Cookies file doesn't appear to be in correct format")
                            return False
                    else:
                        logger.error(f"Failed to fetch cookies. Status: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Error downloading cookies: {e}")
            return False
    
    def start(self, update: Update, context: CallbackContext):
        """Send welcome message"""
        user = update.effective_user
        welcome_text = f"""
🤖 YouTube Video Downloader Bot 🤖

Hello {self.safe_text(user.first_name)}! I can download videos from YouTube and other platforms.

📌 Available Commands:
/start - Show this message
/download [url] - Download video
/settings - Configure download settings
/resolution [360|480|720|1080] - Set video quality
/status - Check bot status

🔧 Admin Commands:
/cookies - Upload cookies.txt file
/update_cookies - Update cookies from COOKIE_URL

⚠️ Note: Maximum file size: {Config.MAX_VIDEO_SIZE}MB
        """
        
        keyboard = [
            [
                InlineKeyboardButton("📥 Download Video", callback_data="download"),
                InlineKeyboardButton("⚙️ Settings", callback_data="settings")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    def safe_text(self, text: str) -> str:
        """Make text safe for Markdown parsing"""
        if not text:
            return ""
        # Escape special Markdown characters
        escape_chars = r'\_*[]()~`>#+-=|{}.!'
        for char in escape_chars:
            text = text.replace(char, f'\\{char}')
        return text
    
    def handle_message(self, update: Update, context: CallbackContext):
        """Handle direct YouTube URLs"""
        if update.message.text and ("youtube.com" in update.message.text or "youtu.be" in update.message.text):
            self.process_download(update, context, update.message.text)
    
    def download_command(self, update: Update, context: CallbackContext):
        """Handle /download command"""
        if not context.args:
            update.message.reply_text("❌ Please provide a YouTube URL.\nUsage: /download https://youtube.com/watch?v=...")
            return
        
        url = context.args[0]
        self.process_download(update, context, url)
    
    def process_download(self, update: Update, context: CallbackContext, url: str):
        """Process video download"""
        user_id = update.effective_user.id
        
        # Check if user already downloading
        if user_id in self.downloading_users:
            update.message.reply_text("⏳ You already have a download in progress. Please wait.")
            return
        
        # Validate URL
        if not self.validate_youtube_url(url):
            update.message.reply_text("❌ Invalid YouTube URL. Please provide a valid YouTube link.")
            return
        
        try:
            self.downloading_users.add(user_id)
            message = update.message.reply_text("🔍 Fetching video information...")
            
            # Get video info
            video_info = self.get_video_info(url)
            if not video_info:
                message.edit_text("❌ Failed to fetch video information. This video might require authentication.")
                return
            
            # Check video size
            if video_info.get('filesize', 0) > Config.MAX_VIDEO_SIZE * 1024 * 1024:
                message.edit_text(f"❌ Video is too large (max {Config.MAX_VIDEO_SIZE}MB)")
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
            message.edit_text(
                f"📹 {title}\n\nSelect download quality:",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error processing download: {e}")
            update.message.reply_text(f"❌ Error: {str(e)}")
        finally:
            self.downloading_users.discard(user_id)
    
    def handle_callback(self, update: Update, context: CallbackContext):
        """Handle button callbacks"""
        query = update.callback_query
        query.answer()
        
        data = query.data
        
        if data == "download":
            query.edit_message_text("📥 Send me a YouTube URL to download")
        
        elif data == "settings":
            self.show_settings(query)
        
        elif data.startswith("dl_"):
            parts = data.split("_")
            if len(parts) >= 3:
                encoded_url = "_".join(parts[1:-1])
                url = self.decode_url(encoded_url)
                quality = parts[-1]
                self.perform_download(query, url, quality)
            elif len(parts) == 2 and parts[1] == "audio":
                encoded_url = data[3:]  # Remove "dl_"
                url = self.decode_url(encoded_url)
                self.perform_download(query, url, "audio")
    
    def encode_url(self, url: str) -> str:
        """Encode URL for callback data"""
        return urllib.parse.quote(url, safe='')
    
    def decode_url(self, encoded_url: str) -> str:
        """Decode URL from callback data"""
        return urllib.parse.unquote(encoded_url)
    
    def perform_download(self, query, url: str, quality: str):
        """Perform the actual download"""
        user_id = query.from_user.id
        
        try:
            query.edit_message_text("⏬ Downloading video...")
            
            # Check if cookies exist
            cookies_file = Config.COOKIES_FILE if os.path.exists(Config.COOKIES_FILE) else None
            if cookies_file:
                logger.info(f"Using cookies file: {cookies_file}")
            else:
                logger.warning("No cookies file found")
            
            # Prepare yt-dlp options with proper cookie handling
            ydl_opts = {
                'format': 'bestaudio/best' if quality == 'audio' else f'best[height<={quality[:-1]}]',
                'outtmpl': f'{Config.DOWNLOAD_PATH}/%(title)s.%(ext)s',
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'cookiefile': cookies_file,
                'cookiesfrombrowser': ('chrome',) if not cookies_file else None,  # Fallback to browser cookies
                'ignoreerrors': True,
                'no_check_certificate': True,
                'prefer_insecure': False,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android', 'web'],
                        'skip': ['dash', 'hls'],
                    }
                }
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Get info first
                info = ydl.extract_info(url, download=False)
                if not info:
                    raise Exception("Could not extract video info")
                
                filename = ydl.prepare_filename(info)
                
                # Download
                ydl.download([url])
            
            # Send file
            self.send_video(query, filename, quality)
            
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            if "Sign in to confirm" in error_msg or "cookies" in error_msg.lower() or "authentication" in error_msg.lower():
                query.edit_message_text(
                    "🔒 This video requires authentication.\n\n"
                    "Possible solutions:\n"
                    "1. Update cookies using /update_cookies command\n"
                    "2. Make sure COOKIE_URL is set correctly\n"
                    "3. Try a different video that doesn't require login"
                )
            else:
                query.edit_message_text(f"❌ Download error: {error_msg[:100]}")
        except Exception as e:
            logger.error(f"Download error: {e}")
            query.edit_message_text(f"❌ Error: {str(e)[:100]}")
    
    def send_video(self, query, filepath: str, quality: str):
        """Send downloaded video to user"""
        try:
            if not os.path.exists(filepath):
                # Try to find the actual downloaded file
                download_dir = Config.DOWNLOAD_PATH
                files = os.listdir(download_dir)
                matching_files = [f for f in files if os.path.splitext(f)[0] in filepath]
                if matching_files:
                    filepath = os.path.join(download_dir, matching_files[0])
                else:
                    raise FileNotFoundError("Downloaded file not found")
            
            file_size = os.path.getsize(filepath) / (1024 * 1024)  # MB
            
            if file_size > 50:  # Telegram file size limit
                # Compress if too large
                query.edit_message_text("📦 File is large, compressing...")
                compressed_path = self.compress_video(filepath)
                file_to_send = compressed_path
            else:
                file_to_send = filepath
            
            # Send file
            with open(file_to_send, 'rb') as video_file:
                if quality == 'audio':
                    query.message.reply_audio(
                        audio=video_file,
                        caption="✅ Audio downloaded successfully!"
                    )
                else:
                    query.message.reply_video(
                        video=video_file,
                        caption=f"✅ Video downloaded in {quality} quality!"
                    )
            
            query.edit_message_text("✅ Download complete!")
            
            # Cleanup
            try:
                os.remove(filepath)
                if file_to_send != filepath and os.path.exists(file_to_send):
                    os.remove(file_to_send)
            except:
                pass
                
        except BadRequest as e:
            if "file is too big" in str(e):
                query.edit_message_text(
                    "❌ File is too large for Telegram.\n"
                    "Try downloading lower quality with /resolution command."
                )
            else:
                query.edit_message_text(f"❌ Error sending file: {str(e)[:100]}")
        except Exception as e:
            logger.error(f"Error sending video: {e}")
            query.edit_message_text(f"❌ Error: {str(e)[:100]}")
    
    def compress_video(self, filepath: str) -> str:
        """Compress video using ffmpeg"""
        output_path = filepath.replace(".mp4", "_compressed.mp4")
        if os.path.exists(output_path):
            os.remove(output_path)
        
        import subprocess
        cmd = [
            'ffmpeg', '-i', filepath,
            '-vcodec', 'libx264',
            '-crf', '28',
            '-preset', 'fast',
            '-acodec', 'aac',
            '-b:a', '128k',
            output_path,
            '-y',
            '-loglevel', 'error'
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr.decode()}")
            return filepath  # Return original if compression fails
    
    def get_video_info(self, url: str) -> dict:
        """Get video information with cookie support"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'cookiefile': Config.COOKIES_FILE if os.path.exists(Config.COOKIES_FILE) else None,
            'ignoreerrors': True,
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
    
    def show_settings(self, query):
        """Show settings menu"""
        cookies_status = "✅ Configured" if os.path.exists(Config.COOKIES_FILE) else "❌ Not configured"
        cookie_url_status = "✅ Set" if Config.COOKIE_URL else "❌ Not set"
        
        settings_text = f"""
⚙️ Download Settings

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
        
        query.edit_message_text(settings_text, reply_markup=reply_markup)
    
    def resolution_command(self, update: Update, context: CallbackContext):
        """Set download resolution"""
        if not context.args:
            resolutions = ["144", "240", "360", "480", "720", "1080"]
            keyboard = [[InlineKeyboardButton(f"{res}p", callback_data=f"set_res_{res}")] for res in resolutions]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            update.message.reply_text(
                "Select default download resolution:",
                reply_markup=reply_markup
            )
            return
        
        try:
            res = int(context.args[0])
            if res in [144, 240, 360, 480, 720, 1080]:
                Config.DEFAULT_RESOLUTION = str(res)
                update.message.reply_text(f"✅ Default resolution set to {res}p")
            else:
                update.message.reply_text("❌ Invalid resolution. Choose from: 144, 240, 360, 480, 720, 1080")
        except ValueError:
            update.message.reply_text("❌ Please provide a valid number")
    
    def handle_document(self, update: Update, context: CallbackContext):
        """Handle document upload (cookies.txt) - Local upload only"""
        user_id = update.effective_user.id
        
        if user_id not in Config.ADMIN_IDS:
            update.message.reply_text("❌ Only admins can upload cookies.")
            return
        
        document = update.message.document
        if not document.file_name.endswith('.txt'):
            update.message.reply_text("❌ Please upload a text file (.txt)")
            return
        
        try:
            # Download the file locally
            file = document.get_file()
            file.download(Config.COOKIES_FILE)
            
            update.message.reply_text(
                f"✅ Cookies uploaded successfully!\n"
                f"File saved as: {Config.COOKIES_FILE}"
            )
                
        except Exception as e:
            logger.error(f"Error handling cookies: {e}")
            update.message.reply_text(f"❌ Error: {str(e)[:100]}")
    
    def update_cookies(self, update: Update, context: CallbackContext):
        """Update cookies from COOKIE_URL"""
        user_id = update.effective_user.id
        
        if user_id not in Config.ADMIN_IDS:
            update.message.reply_text("❌ Only admins can update cookies.")
            return
        
        if not Config.COOKIE_URL:
            update.message.reply_text("❌ COOKIE_URL environment variable not configured.")
            return
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(self.download_cookies_from_url(Config.COOKIE_URL))
            
            if success:
                update.message.reply_text("✅ Cookies updated from COOKIE_URL!")
            else:
                update.message.reply_text("❌ Failed to update cookies from COOKIE_URL")
                        
        except Exception as e:
            logger.error(f"Error updating cookies: {e}")
            update.message.reply_text(f"❌ Error: {str(e)[:100]}")
    
    def status_command(self, update: Update, context: CallbackContext):
        """Show bot status"""
        downloads_count = len(self.downloading_users)
        cookies_status = "✅ Configured" if os.path.exists(Config.COOKIES_FILE) else "❌ Not configured"
        cookie_url_status = "✅ Set" if Config.COOKIE_URL else "❌ Not set"
        
        status_text = f"""
📊 Bot Status

👥 Active Downloads: {downloads_count}
🍪 Local Cookies: {cookies_status}
🔗 COOKIE_URL: {cookie_url_status}
💾 Storage: {self.get_free_space()} free
        """
        
        update.message.reply_text(status_text)
    
    def get_free_space(self):
        """Get free disk space"""
        try:
            total, used, free = shutil.disk_usage(Config.DOWNLOAD_PATH)
            free_gb = free / (1024**3)
            return f"{free_gb:.1f}GB"
        except:
            return "Unknown"
    
    def error_handler(self, update: Update, context: CallbackContext):
        """Handle errors"""
        try:
            error_msg = str(context.error) if context.error else "Unknown error"
            logger.error(f"Bot error: {error_msg}")
            
            if update and update.effective_message:
                # Send simple text without Markdown
                update.effective_message.reply_text(
                    "❌ An error occurred. Please try again later."
                )
        except Exception as e:
            logger.error(f"Error in error handler: {e}")

def main():
    """Start the bot"""
    if not Config.BOT_TOKEN:
        logger.error("BOT_TOKEN not set in environment variables")
        return
    
    # Create updater
    updater = Updater(Config.BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    
    # Create bot instance
    bot = YouTubeDownloaderBot(updater)
    
    # Add handlers
    dp.add_handler(CommandHandler("start", bot.start))
    dp.add_handler(CommandHandler("download", bot.download_command))
    dp.add_handler(CommandHandler("resolution", bot.resolution_command))
    dp.add_handler(CommandHandler("cookies", bot.handle_document, filters=Filters.document))
    dp.add_handler(CommandHandler("update_cookies", bot.update_cookies))
    dp.add_handler(CommandHandler("status", bot.status_command))
    dp.add_handler(CommandHandler("settings", lambda u, c: bot.show_settings(u.callback_query) if u.callback_query else u.message.reply_text("Use /settings in response to a message")))
    
    # Message handlers
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, bot.handle_message))
    dp.add_handler(MessageHandler(Filters.document, bot.handle_document))
    
    # Callback handler
    dp.add_handler(CallbackQueryHandler(bot.handle_callback))
    
    # Error handler
    dp.add_error_handler(bot.error_handler)
    
    # Start bot
    logger.info("Bot starting...")
    logger.info(f"BOT_TOKEN: {'Set' if Config.BOT_TOKEN else 'Not set'}")
    logger.info(f"ADMIN_IDS: {Config.ADMIN_IDS}")
    logger.info(f"COOKIE_URL: {Config.COOKIE_URL}")
    logger.info(f"Cookies file exists: {os.path.exists(Config.COOKIES_FILE)}")
    
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()