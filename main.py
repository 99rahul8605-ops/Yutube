import os
import re
import logging
import asyncio
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import BadRequest
import yt_dlp
import requests
import aiohttp
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
        self.cookies_url = None
        
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
/update_cookies - Update cookies from batbin

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
                            callback_data=f"dl_{url}_{fmt['height']}")
                        ])
            
            # Add audio only option
            keyboard.append([
                InlineKeyboardButton("🎵 Audio Only", callback_data=f"dl_{url}_audio")
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
                url = "_".join(parts[1:-1])
                quality = parts[-1]
                await self.perform_download(query, url, quality)
    
    async def perform_download(self, query, url: str, quality: str):
        """Perform the actual download"""
        user_id = query.from_user.id
        
        try:
            await query.edit_message_text("⏬ Downloading video...")
            
            # Prepare yt-dlp options
            ydl_opts = {
                'format': 'bestaudio/best' if quality == 'audio' else f'best[height<={quality}]',
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
                    "An admin needs to upload cookies.txt file using /cookies command."
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
            r'(https?://)?(www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)'
        ]
        
        for pattern in patterns:
            if re.match(pattern, url):
                return True
        return False
    
    async def show_settings(self, query):
        """Show settings menu"""
        settings_text = f"""
⚙️ *Download Settings*

📏 Max File Size: {Config.MAX_VIDEO_SIZE}MB
🎬 Default Resolution: {Config.DEFAULT_RESOLUTION}p
🍪 Cookies: {'✅ Configured' if os.path.exists(Config.COOKIES_FILE) else '❌ Not configured'}

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
        """Handle document upload (cookies.txt)"""
        user_id = update.effective_user.id
        
        if user_id not in Config.ADMIN_IDS:
            await update.message.reply_text("❌ Only admins can upload cookies.")
            return
        
        document = update.message.document
        if document.file_name != "cookies.txt":
            await update.message.reply_text("❌ Please upload a file named 'cookies.txt'")
            return
        
        try:
            # Download the file
            file = await document.get_file()
            await file.download_to_drive(Config.COOKIES_FILE)
            
            # Upload to batbin
            with open(Config.COOKIES_FILE, 'r') as f:
                cookies_content = f.read()
            
            response = requests.post('https://batbin.me/api/v2/paste', json={'content': cookies_content})
            
            if response.status_code == 201:
                paste_id = response.json()['key']
                self.cookies_url = f"https://batbin.me/{paste_id}"
                
                await update.message.reply_text(
                    f"✅ Cookies uploaded successfully!\n"
                    f"📁 URL: {self.cookies_url}\n"
                    f"Cookies will be used for age-restricted videos."
                )
            else:
                await update.message.reply_text("✅ Cookies saved locally but failed to upload to batbin.")
                
        except Exception as e:
            logger.error(f"Error handling cookies: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)[:100]}")
    
    async def update_cookies(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Update cookies from batbin"""
        user_id = update.effective_user.id
        
        if user_id not in Config.ADMIN_IDS:
            await update.message.reply_text("❌ Only admins can update cookies.")
            return
        
        if not self.cookies_url:
            await update.message.reply_text("❌ No cookies URL configured. Upload cookies first.")
            return
        
        try:
            # Download from batbin
            response = requests.get(self.cookies_url)
            
            if response.status_code == 200:
                with open(Config.COOKIES_FILE, 'w') as f:
                    f.write(response.text)
                
                await update.message.reply_text("✅ Cookies updated from batbin!")
            else:
                await update.message.reply_text("❌ Failed to fetch cookies from batbin.")
                
        except Exception as e:
            logger.error(f"Error updating cookies: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)[:100]}")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show bot status"""
        downloads_count = len(self.downloading_users)
        cookies_status = "✅ Configured" if os.path.exists(Config.COOKIES_FILE) else "❌ Not configured"
        
        status_text = f"""
📊 *Bot Status*

👥 Active Downloads: {downloads_count}
🍪 Cookies: {cookies_status}
💾 Storage: {self.get_free_space()} free
🔄 Uptime: {self.get_uptime()}
        """
        
        await update.message.reply_text(status_text, parse_mode='Markdown')
    
    def get_free_space(self):
        """Get free disk space"""
        stat = os.statvfs(Config.DOWNLOAD_PATH)
        free = stat.f_bavail * stat.f_frsize / (1024 * 1024 * 1024)  # GB
        return f"{free:.1f}GB"
    
    def get_uptime(self):
        """Get bot uptime"""
        # Simplified - in production use proper uptime tracking
        return "Running"
    
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
    application.add_handler(CommandHandler("cookies", bot.handle_document, filters.Document.ALL))
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
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
