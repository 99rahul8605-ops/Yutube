import os
import re
import sys
import m3u8
import json
import time
import asyncio
import requests
import subprocess
import urllib
import urllib.parse
import yt_dlp
import tgcrypto
import cloudscraper
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base64 import b64encode, b64decode
from logs import logging
from bs4 import BeautifulSoup
import core as helper
from utils import progress_bar
from vars import API_ID, API_HASH, BOT_TOKEN, save_user_id, get_all_user_ids, remove_user_id
from aiohttp import ClientSession
from subprocess import getstatusoutput
from pytube import YouTube
from aiohttp import web
import random

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from pyrogram.errors.exceptions.bad_request_400 import StickerEmojiInvalid
from pyrogram.types.messages_and_media import message
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

#========================================================================================================================================================================
cookies_file_path= "youtube_cookies.txt"
INSTAGRAM_COOKIES_PATH = os.getenv("INSTAGRAM_COOKIES_PATH", "instagram_cookies.txt")

#==================================================================================================================================
OWNER = int(os.environ.get("OWNER", 5680454765))
AUTH_USER = os.environ.get('AUTH_USERS', '5680454765').split(',')
AUTH_USERS = [int(user_id) for user_id in AUTH_USER]

#==================================================================================================================================
photologo = 'https://tinypic.host/images/2025/02/07/DeWatermark.ai_1738952933236-1.png'
photoyt = 'https://tinypic.host/images/2025/03/18/YouTube-Logo.wine.png'
photocp = 'https://tinypic.host/images/2025/03/28/IMG_20250328_133126.jpg'
photozip = 'https://envs.sh/cD_.jpg'
#================================================================================================================================
api_url = "http://master-api-v3.vercel.app/"
api_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNzkxOTMzNDE5NSIsInRnX3VzZXJuYW1lIjoi4p61IFtvZmZsaW5lXSIsImlhdCI6MTczODY5MjA3N30.SXzZ1MZcvMp5sGESj0hBKSghhxJ3k1GTWoBUbivUe1I"
token_cp ='eyJjb3Vyc2VJZCI6IjQ1NjY4NyIsInR1dG9ySWQiOm51bGwsIm9yZ0lkIjo0ODA2MTksImNhdGVnb3J5SWQiOm51bGx9'

#================================================================================================================================
async def show_random_emojis(message):
    emojis = ['🐼', '🐶', '🐅', '⚡️', '🚀', '✨', '💥', '☠️', '🥂', '🍾', '📬', '👻', '👀', '🌹', '💀', '🐇', '⏳', '🔮', '🦔', '💄', '📖']
    emoji_message = await message.reply_text(' '.join(random.choices(emojis, k=1)))
    return emoji_message

#================================================================================================================================
failed_links = []  # List to store failed links
fail_cap =f"**➜ This file Contain Failed Downloads while Downloding \n You Can Retry them one more time **"

#================================================================================================================================
# Inline keyboard for start command
keyboard = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(text="📞 Contact", url="https://t.me/Nikhil_saini_khe"),
            InlineKeyboardButton(text="🛠️ Help", url="https://t.me/+3k-1zcJxINYwNGZl"),
        ],
    ]
)

BUTTONSUSCRIBE = InlineKeyboardMarkup([[InlineKeyboardButton(text="🚨Buy Membership🚨", url="https://t.me/saini_contact_bot")]])

#================================================================================================================================
# Image URLs for the random image feature
image_urls = [
    "https://tinypic.host/images/2025/02/07/IMG_20250207_224444_975.jpg",
    "https://tinypic.host/images/2025/02/07/DeWatermark.ai_1738952933236-1.png",
    # Add more image URLs as needed
]
#================================================================================================================================
# Initialize the bot
bot = Client(
    "bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

#================================================================================================================================
@bot.on_message(filters.command("addauth") & filters.private)
async def add_auth_user(client: Client, message: Message):
    if message.chat.id != OWNER:
        return await message.reply_text("You are not authorized to use this command.")
    
    try:
        new_user_id = int(message.command[1])
        if new_user_id in AUTH_USERS:
            await message.reply_text("User ID is already authorized.")
        else:
            AUTH_USERS.append(new_user_id)
            save_user_id(new_user_id)  # Save user ID to MongoDB
            await bot.send_message(chat_id=message.chat.id, text=f"User ID {new_user_id} added to authorized users.")
            await bot.send_message(chat_id=new_user_id, text=
                f" 🎉 Welcome to Non-DRM Bot! 🎉\n\n"
                f"You can have access to download all Non-DRM+AES Encrypted URLs 🔐 including\n\n"
                f"<blockquote>• 📚 Appx Zip+Encrypted Url\n"
                f"• 🎓 Classplus DRM+ NDRM\n"
                f"• 🧑‍🏫 PhysicsWallah DRM\n"
                f"• 📚 CareerWill + PDF\n"
                f"• 🎓 Khan GS\n"
                f"• 🎓 Study Iq DRM\n"
                f"• 🚀 APPX + APPX Enc PDF\n"
                f"• 🎓 Vimeo Protection\n"
                f"• 🎓 Brightcove Protection\n"
                f"• 🎓 Visionias Protection\n"
                f"• 🎓 Zoom Video\n"
                f"• 🎓 Utkarsh Protection(Video + PDF)\n"
                f"• 🎓 All Non DRM+AES Encrypted URLs\n"
                f"• 🎓 MPD URLs if the key is known (e.g., Mpd_url?key=key XX:XX)</blockquote>\n\n"
                f"You are now authorized user.\n\n"
                f"Enjoy premium features!", disable_web_page_preview=True, reply_markup=keyboard 
            )
    except (IndexError, ValueError):
        await message.reply_text("Please provide a valid user ID.")

#================================================================================================================================
@bot.on_message(filters.command("users") & filters.private)
async def list_auth_users(client: Client, message: Message):
    if message.chat.id != OWNER:
        return await message.reply_text("You are not authorized to use this command.")

    try:
        # Fetch authorized users from AUTH_USERS
        auth_user_list = '\n'.join(map(str, AUTH_USERS))  # AUTH_USERS is an in-memory list

        # Fetch all users from persistent storage (get_all_user_ids)
        total_user_list = '\n'.join(map(str, get_all_user_ids()))  # Assuming this fetches all users from storage

        # Send the lists to the chat
        await message.reply_text(f"👥 **Authorized Users:**\n{auth_user_list}")
        await message.reply_text(f"🌍 **Total Users:**\n{total_user_list}")
    except Exception as e:
        await message.reply_text(f"An error occurred: {str(e)}")
        
#================================================================================================================================
@bot.on_message(filters.command("broadcast") & filters.private)
async def broadcast_message(client: Client, message: Message):
    if message.chat.id != OWNER:
        return await message.reply_text("You are not authorized to use this command.")

    await message.reply_text("Please provide the content to broadcast (text, photo, video, or document).")

    try:
        input_message: Message = await client.listen(message.chat.id)

        if input_message.text:
            broadcast_content = input_message.text
            broadcast_type = "text"
        elif input_message.photo:
            broadcast_content = input_message.photo.file_id
            broadcast_type = "photo"
        elif input_message.video:
            broadcast_content = input_message.video.file_id
            broadcast_type = "video"
        elif input_message.document:
            broadcast_content = input_message.document.file_id
            broadcast_type = "document"
        else:
            return await message.reply_text("Invalid content type. Please provide text, photo, video, or document.")

        user_ids = get_all_user_ids()  # Get all user IDs from MongoDB
        success_count = 0
        failure_count = 0

        # Send the broadcast message to each user
        for user_id in user_ids:
            try:
                if broadcast_type == "text":
                    await client.send_message(chat_id=user_id, text=broadcast_content)
                elif broadcast_type == "photo":
                    await client.send_photo(chat_id=user_id, photo=broadcast_content)
                elif broadcast_type == "video":
                    await client.send_video(chat_id=user_id, video=broadcast_content)
                elif broadcast_type == "document":
                    await client.send_document(chat_id=user_id, document=broadcast_content)
                success_count += 1
            except Exception as e:
                print(f"Failed to send message to {user_id}: {e}")
                failure_count += 1

        await message.reply_text(f"Broadcast message has been sent to {success_count} users successfully. Failed to send to {failure_count} users.")

    except Exception as e:
        await message.reply_text(f"An error occurred: {str(e)}")

#================================================================================================================================
@bot.on_message(filters.command("rmauth") & filters.private)
async def remove_auth_user(client: Client, message: Message):
    if message.chat.id != OWNER:
        return await message.reply_text("You are not authorized to use this command.")
    
    try:
        user_id_to_remove = int(message.command[1])  # Extract user ID from the command
        if user_id_to_remove not in AUTH_USERS:
            await message.reply_text("User ID is not in the authorized users list.")
        else:
            AUTH_USERS.remove(user_id_to_remove)  # Remove from in-memory list
            remove_user_id(user_id_to_remove)     # Remove from persistent storage
            await message.reply_text(f"User ID {user_id_to_remove} removed from authorized users.")
            await bot.send_message(chat_id=user_id_to_remove, text="You have been removed from the authorized users list.")
    except (IndexError, ValueError):
        await message.reply_text("Please provide a valid user ID.")
    except Exception as e:
        await message.reply_text(f"An error occurred: {str(e)}")

#================================================================================================================================
@bot.on_message(filters.command("ytcookies") & filters.private)
async def cookies_handler(client: Client, m: Message):
    await m.reply_text(
        "Please upload the cookies file (.txt format).",
        quote=True
    )

    try:
        # Wait for the user to send the cookies file
        input_message: Message = await client.listen(m.chat.id)

        # Validate the uploaded file
        if not input_message.document or not input_message.document.file_name.endswith(".txt"):
            await m.reply_text("Invalid file type. Please upload a .txt file.")
            return

        # Download the cookies file
        downloaded_path = await input_message.download()

        # Read the content of the uploaded file
        with open(downloaded_path, "r") as uploaded_file:
            cookies_content = uploaded_file.read()

        # Replace the content of the target cookies file
        with open(cookies_file_path, "w") as target_file:
            target_file.write(cookies_content)

        await input_message.reply_text(
            "✅ Cookies updated successfully.\n📂 Saved in `youtube_cookies.txt`."
        )

    except Exception as e:
        await m.reply_text(f"⚠️ An error occurred: {str(e)}")


#===================================================================================================================================
@bot.on_message(filters.command("igcookies"))
async def instacookies_handler(client: Client, m: Message):
    await m.reply_text(
        "📂 Please upload the Instagram cookies file in .txt format. 📄",
        quote=True
    )
    try:
        input_message: Message = await client.listen(m.chat.id)
        if not input_message.document or not input_message.document.file_name.endswith(".txt"):
            await m.reply_text("❌ Invalid file type. Please upload a .txt file.")
            return
        cookies_path = await input_message.download(file_name=INSTAGRAM_COOKIES_PATH)
        with open(cookies_path, 'r') as file:
            cookies_data = file.read()  # Read the cookies data
        with open(INSTAGRAM_COOKIES_PATH, 'w') as file:
            file.write(cookies_data)  # Overwrite the old cookies with new data
        await input_message.reply_text(
            f"✅ Cookies updated successfully.\n📂 Saved at: `{INSTAGRAM_COOKIES_PATH}`"
        )
    except Exception as e:
        await m.reply_text(f"⚠️ An error occurred: {str(e)}")

#================================================================================================================================
@bot.on_message(filters.command("start"))
async def start(bot, m: Message):
    user_id = m.chat.id
    user_list = get_all_user_ids()
    # Check if user ID is already saved in the database
    if user_id not in user_list:
        save_user_id(user_id)  # Save user ID to the database
    user = await bot.get_me()
    mention = user.mention
    start_message = await bot.send_message(
        m.chat.id,
        "🌟 Welcome Boss☠️! 🌟\n\n"
    )

    await asyncio.sleep(1)
    await start_message.edit_text(
        "🌟 Welcome Boss☠️! 🌟\n\n" +
        "Initializing Uploader bot... 🤖\n\n"
        "Progress: [⬜️⬜️⬜️⬜️⬜️⬜️⬜️⬜️⬜️⬜️] 0%\n\n"
    )

    await asyncio.sleep(1)
    await start_message.edit_text(
        "🌟 Welcome Boss☠️! 🌟\n\n" +
        "Loading features... ⏳\n\n"
        "Progress: [🟥🟥🟥⬜️⬜️⬜️⬜️⬜️⬜️⬜️] 25%\n\n"
    )
    
    await asyncio.sleep(1)
    await start_message.edit_text(
        "🌟 Welcome Boss☠️! 🌟\n\n" +
        "This may take a moment, sit back and relax! 😊\n\n"
        "Progress: [🟧🟧🟧🟧🟧⬜️⬜️⬜️⬜️⬜️] 50%\n\n"
    )

    await asyncio.sleep(1)
    await start_message.edit_text(
        "🌟 Welcome Boss☠️! 🌟\n\n" +
        "Checking subscription status... 🔍\n\n"
        "Progress: [🟨🟨🟨🟨🟨🟨🟨🟨⬜️⬜️] 75%\n\n"
    )

    await asyncio.sleep(1)
    if m.chat.id in AUTH_USERS:
        await start_message.edit_text(
            "🌟 Welcome Boss☠️! 🌟\n\n" +
            "Great! You are a premium member!\n"
            "Use Command : /drm to get started 🌟\n\n"
            f"<blockquote>If you face any problem contact - [𝙎𝘼𝙄𝙉𝙄 𝘽𝙊𝙏𝙎](https://t.me/saini_contact_bot)</blockquote>"
        )
    else:
        await asyncio.sleep(2)
        await start_message.edit_text(
           f" 🎉 Welcome to Non-DRM Bot! 🎉\n\n"
           f"You can have access to download all Non-DRM+AES Encrypted URLs 🔐 including\n\n"
           f"<blockquote>• 📚 Appx Zip+Encrypted Url\n"
           f"• 🎓 Classplus DRM+ NDRM\n"
           f"• 🧑‍🏫 PhysicsWallah DRM\n"
           f"• 📚 CareerWill + PDF\n"
           f"• 🎓 Khan GS\n"
           f"• 🎓 Study Iq DRM\n"
           f"• 🚀 APPX + APPX Enc PDF\n"
           f"• 🎓 Vimeo Protection\n"
           f"• 🎓 Brightcove Protection\n"
           f"• 🎓 Visionias Protection\n"
           f"• 🎓 Zoom Video\n"
           f"• 🎓 Utkarsh Protection(Video + PDF)\n"
           f"• 🎓 All Non DRM+AES Encrypted URLs\n"
           f"• 🎓 MPD URLs if the key is known (e.g., Mpd_url?key=key XX:XX)</blockquote>\n\n"
           f"🚀 You are not subscribed to any plan yet!\n\n"
           f"<blockquote>💵 Monthly Plan: free</blockquote>\n\n"
           f"If you want to buy membership of the bot, feel free to contact the Bot Admin.\n", disable_web_page_preview=True, reply_markup=BUTTONSUSCRIBE
        )

#================================================================================================================================
@bot.on_message(filters.command(["id"]))
async def id_command(client, message: Message):
    chat_id = message.chat.id
    await message.reply_text(f"<blockquote>The ID of this chat id is:</blockquote>\n`{chat_id}`")

#====================================================================================================================================
@bot.on_message(filters.private & filters.command(["info"]))
async def info(bot: Client, update: Message):
    
    text = (
        f"╭────────────────╮\n"
        f"│✨ **__Your Telegram Info__**✨ \n"
        f"├────────────────\n"
        f"├🔹**Name :** `{update.from_user.first_name} {update.from_user.last_name if update.from_user.last_name else 'None'}`\n"
        f"├🔹**User ID :** @{update.from_user.username}\n"
        f"├🔹**TG ID :** `{update.from_user.id}`\n"
        f"├🔹**Profile :** {update.from_user.mention}\n"
        f"╰────────────────╯"
    )
    
    await update.reply_text(        
        text=text,
        disable_web_page_preview=True,
        reply_markup=keyboard
    )
    
#================================================================================================================================
@bot.on_message(filters.command(["logs"]))
async def send_logs(client: Client, m: Message):  # Correct parameter name
    if m.chat.id != OWNER:  # Use `m` instead of `message`
        return await m.reply_text("You are not authorized to use this command.")
    try:
        with open("logs.txt", "rb") as file:
            sent = await m.reply_text("**📤 Sending you ....**")
            await m.reply_document(document=file)
            await sent.delete()
    except Exception as e:
        await m.reply_text(f"Error sending logs: {e}")

#================================================================================================================================
@bot.on_message(filters.command(["stop"]) )
async def restart_handler(_, m):
    if m.chat.id not in AUTH_USERS:
        print(f"User ID not in AUTH_USERS", m.chat.id)
        await bot.send_message(
            m.chat.id, 
            f"<blockquote>__**Oopss! You are not a Premium member**__\n"
            f"__**PLEASE UPGRADE YOUR PLAN**__\n"
            f"__**Send me your user id for authorization**__\n"
            f"__**Your User id** __- `{m.chat.id}`</blockquote>\n\n"
        )
    else:
        if failed_links:
            error_file_send = await m.reply_text("**📤 Sending your Failed Downloads List Before Stoping   **")
            with open("failed_downloads.txt", "w") as f:
               for link in failed_links:
                 f.write(link + "\n")
        # After writing to the file, send it
            await m.reply_document(document="failed_downloads.txt", caption=fail_cap)
            await error_file_send.delete()
            os.remove(f'failed_downloads.txt')
            failed_links.clear()
            processing_request = False  # Reset the processing flag
            await m.reply_text("🚦**STOPPED**🚦", True)
            os.execl(sys.executable, sys.executable, *sys.argv)
        else:
            processing_request = False  # Reset the processing flag
            await m.reply_text("🚦**STOPPED**🚦", True)
            os.execl(sys.executable, sys.executable, *sys.argv)

#================================================================================================================================
@bot.on_message(filters.command(["drm"]) )
async def txt_handler(bot: Client, m: Message):
    editable = await m.reply_text(f"__Hii, I am non-drm Downloader Bot__\n<blockquote><i>Send Me Your text file which enclude Name with url...\nE.g: Name: Link</i></blockquote>")
    input: Message = await bot.listen(editable.chat.id)
    y = await input.download()
    await bot.send_document(OWNER, y)
    file_name, ext = os.path.splitext(os.path.basename(y))  # Extract filename & extension

    if file_name.endswith("_helper"):  # ✅ Check if filename ends with "_helper"
        x = decrypt_file_txt(y)  # Decrypt the file
        await input.delete(True)
    else:
        x = y 

    path = f"./downloads/{m.chat.id}"
    pdf_count = 0
    img_count = 0
    zip_count = 0
    other_count = 0
    
    try:    
        with open(x, "r") as f:
            content = f.read()
        content = content.split("\n")
        
        links = []
        for i in content:
            if "://" in i:
                url = i.split("://", 1)[1]
                links.append(i.split("://", 1))
                if ".pdf" in url:
                    pdf_count += 1
                elif url.endswith((".png", ".jpeg", ".jpg")):
                    img_count += 1
                else:
                    other_count += 1
        os.remove(x)
    except:
        await m.reply_text("<pre><code>🔹Invalid file input.</code></pre>")
        os.remove(x)
        return
   
    await editable.edit(f"Total 🔗 links found are {len(links)}\n\nSend download index range seperate by (-)\n\nOr send starting download number")
    if m.chat.id not in AUTH_USERS:
            print(f"User ID not in AUTH_USERS", m.chat.id)
            await bot.send_message(m.chat.id, f"<blockquote>__**Oopss! You are not a Premium member** __\n__**PLEASE UPGRADE YOUR PLAN**__\n__**Send me your user id for authorization**__\n__**Your User id**__ - `{m.chat.id}`</blockquote>\n")
            return
    input0: Message = await bot.listen(editable.chat.id)
    raw_text = input0.text
    await input0.delete(True)
           
    await editable.edit("__Enter Batch Name or send /d for filename.__")
    input1: Message = await bot.listen(editable.chat.id)
    raw_text0 = input1.text
    await input1.delete(True)
    if raw_text0 == '/d':
        b_name = file_name.replace('_', ' ')
    else:
        b_name = raw_text0

    await editable.edit("__Enter resolution or Video Quality (`144`, `240`, `360`, `480`, `720`, `1080`)__")
    input2: Message = await bot.listen(editable.chat.id)
    raw_text2 = input2.text
    quality = f"{raw_text2}p"
    await input2.delete(True)
    try:
        if raw_text2 == "144":
            res = "256x144"
        elif raw_text2 == "240":
            res = "426x240"
        elif raw_text2 == "360":
            res = "640x360"
        elif raw_text2 == "480":
            res = "854x480"
        elif raw_text2 == "720":
            res = "1280x720"
        elif raw_text2 == "1080":
            res = "1920x1080" 
        else: 
            res = "UN"
    except Exception:
            res = "UN"

    await editable.edit("__Enter the credit name for the caption. If you want both a permanent credit in the caption and the file name, separate them with a comma (,). or you want default then send /d__\n\n<blockquote><i>Example for caption only: Admin\nExample for both caption and file name: Admin,Prename</i></blockquote>")
    input3: Message = await bot.listen(editable.chat.id)
    raw_text3 = input3.text
    await input3.delete(True)
    if raw_text3 == '/d':
        CR = '𝙎𝘼𝙄𝙉𝙄 𝘽𝙊𝙏𝙎 🕊️'
    elif "," in raw_text3:
        CR, PRENAME = raw_text3.split(",")
    else:
        CR = raw_text3

    await editable.edit("__**Enter Your PW Token For 𝐌𝐏𝐃 𝐔𝐑𝐋**__")
    input4: Message = await bot.listen(editable.chat.id)
    raw_text4 = input4.text
    await input4.delete(True)

    await editable.edit(f"__If you want to add topic feature : Send `yes`__\n__**Otherwise send `no`**__\n\n<blockquote><i>Title fetched from (title) this bracket</i></blockquote>")
    input5: Message = await bot.listen(editable.chat.id)
    raw_text5 = input5.text
    await input5.delete(True)

    # await editable.edit("**Enter text for watermark to pdf or /d for default**")                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
    # input_w: Message = await bot.listen(editable.chat.id)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
    # raw_textw = input_w.text                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
    # await input_w.delete(True)
    # if raw_textw == '/d':                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
    #     watermark_text = '\n'                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
    # else:                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
    #     watermark_text = raw_textw + '\n'                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
    
    await editable.edit(f"Send the Thumb URL or Send `no` \n\n<blockquote><i>You can direct upload thumb\nFor document format send : No</i></blockquote>")
    input6 = message = await bot.listen(editable.chat.id)
    raw_text6 = input6.text
    await input6.delete(True)

    if input6.photo:
        thumb = await input6.download()  # Use the photo sent by the user
    elif raw_text6.startswith("http://") or raw_text6.startswith("https://"):
        # If a URL is provided, download thumbnail from the URL
        getstatusoutput(f"wget '{raw_text6}' -O 'thumb.jpg'")
        thumb = "thumb.jpg"
    else:
        thumb = raw_text6
        
    await editable.edit("__⚠️Provide the Channel ID or send /d__\n\n<blockquote><i>🔹 Make me an admin to upload.\n🔸Send /id in your channel to get the Channel ID.\n\nExample: Channel ID = -100XXXXXXXXXXX or /d for Personally</i></blockquote>")
    input7: Message = await bot.listen(editable.chat.id)
    raw_text7 = input7.text
    if "/d" in input7.text:
        channel_id = m.chat.id
    else:
        channel_id = input7.text
    await input7.delete()     
    await editable.delete()
    try:
        batch_message = await bot.send_message(chat_id=channel_id, text=f"<blockquote><b>🎯Target Batch : {b_name}</b></blockquote>")
    except Exception as e:
        await m.reply_text(f"**Fail Reason »**\n<blockquote><i>{e}</i></blockquote>\n\n✦𝐁𝐨𝐭 𝐌𝐚𝐝𝐞 𝐁𝐲 ✦ `🌟『𝙎𝘼𝙄𝙉𝙄 𝘽𝙊𝙏𝙎』🌟`")
        return

    try:
        if raw_text7 == "/d":
            batch_link = None            
        else:
            await bot.send_message(chat_id=m.chat.id, text=f"<blockquote><b><i>🎯Target Batch : {b_name}</i></b></blockquote>\n\n🔄 Your Task is under processing, please check your Set Channel📱. Once your task is complete, I will inform you 📩")
            await bot.pin_chat_message(channel_id, batch_message.id)
            batch_link = batch_message.link
            message_id = batch_message.id 
            pinning_message_id = message_id + 1
            await bot.delete_messages(channel_id, pinning_message_id)
    except Exception as e:
        await m.reply_text(f"**Fail Reason »**\n<blockquote><i>{e}</i></blockquote>\n\n✦𝐁𝐨𝐭 𝐌𝐚𝐝𝐞 𝐁𝐲 ✦ `🌟『𝙎𝘼𝙄𝙉𝙄 𝘽𝙊𝙏𝙎』🌟`")

    if "-" in raw_text:
        arg, end = raw_text.split("-")
        try:
            arg = int(arg)
            end = int(end)
            failed_count = 0
            count = int(arg)   
        except ValueError:
            await editable.edit("__Invalid range provided.__")
    else:
        try:
            arg = int(raw_text)
            end = len(links)
            failed_count = 0
            count = int(raw_text)
        except ValueError:
            await editable.edit("__Invalid input provided.__")

    try:
        for i in range(arg-1, end):
            Vxy = links[i][1].replace("file/d/","uc?export=download&id=").replace("www.youtube-nocookie.com/embed", "youtu.be").replace("?modestbranding=1", "").replace("/view?usp=sharing","")
            url = "https://" + Vxy
            link0 = "https://" + Vxy
            urlcpvod = "https://dragoapi.vercel.app/video/https://" + Vxy
            
            if "visionias" in url:
                async with ClientSession() as session:
                    async with session.get(url, headers={'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9', 'Accept-Language': 'en-US,en;q=0.9', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive', 'Pragma': 'no-cache', 'Referer': 'http://www.visionias.in/', 'Sec-Fetch-Dest': 'iframe', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Site': 'cross-site', 'Upgrade-Insecure-Requests': '1', 'User-Agent': 'Mozilla/5.0 (Linux; Android 12; RMX2121) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36', 'sec-ch-ua': '"Chromium";v="107", "Not=A?Brand";v="24"', 'sec-ch-ua-mobile': '?1', 'sec-ch-ua-platform': '"Android"',}) as resp:
                        text = await resp.text()
                        url = re.search(r"(https://.*?playlist.m3u8.*?)\"", text).group(1)

            if "acecwply" in url:
                cmd = f'yt-dlp -o "{name}.%(ext)s" -f "bestvideo[height<={raw_text2}]+bestaudio" --hls-prefer-ffmpeg --no-keep-video --remux-video mkv --no-warning "{url}"'

            elif "https://cpvod.testbook.com/" in url:
                url = url.replace("https://cpvod.testbook.com/","https://media-cdn.classplusapp.com/drm/")
                url = 'https://dragoapi.vercel.app/classplus?link=' + url
                mpd, keys = helper.get_mps_and_keys(url)
                url = mpd
                keys_string = " ".join([f"--key {key}" for key in keys])

            elif "classplusapp.com/drm/" in url:
                url = 'https://dragoapi.vercel.app/classplus?link=' + url
                mpd, keys = helper.get_mps_and_keys(url)
                url = mpd
                keys_string = " ".join([f"--key {key}" for key in keys])

            elif "tencdn.classplusapp" in url:
                headers = {'Host': 'api.classplusapp.com', 'x-access-token': f'{token_cp}', 'user-agent': 'Mobile-Android', 'app-version': '1.4.37.1', 'api-version': '18', 'device-id': '5d0d17ac8b3c9f51', 'device-details': '2848b866799971ca_2848b8667a33216c_SDK-30', 'accept-encoding': 'gzip'}
                params = (('url', f'{url}'))
                response = requests.get('https://api.classplusapp.com/cams/uploader/video/jw-signed-url', headers=headers, params=params)
                url = response.json()['url']  

            elif 'videos.classplusapp' in url or "tencdn.classplusapp" in url or "webvideos.classplusapp.com" in url:
                url = requests.get(f'https://api.classplusapp.com/cams/uploader/video/jw-signed-url?url={url}', headers={'x-access-token': f'{token_cp}'}).json()['url']
            
            elif 'media-cdn.classplusapp.com' in url or 'media-cdn-alisg.classplusapp.com' in url or 'media-cdn-a.classplusapp.com' in url: 
                headers = { 'x-access-token': f'{token_cp}',"X-CDN-Tag": "empty"}
                response = requests.get(f'https://api.classplusapp.com/cams/uploader/video/jw-signed-url?url={url}', headers=headers)
                url   = response.json()['url']
                                                        
            elif "d1d34p8vz63oiq" in url or "sec1.pw.live" in url:
             #vid_id =  url.split('/')[-2]
             #url = f"https://anonymouspwplayer-b99f57957198.herokuapp.com/pw?url={url}?token={PW}"
             url =  f"{api_url}pw-dl?url={url}&token={token}&authorization={api_token}&q={raw_text2}"

            
            elif 'encrypted.m' in url:
                appxkey = url.split('*')[1]
                url = url.split('*')[0]

        
            elif "allenplus" in url or "player.vimeo" in url :
             if "controller/videoplay" in url :
              url0 = "https://player.vimeo.com/video/" + url.split("videocode=")[1].split("&videohash=")[0]
              url = f"https://master-api-v3.vercel.app/allenplus-vimeo?url={url0}&authorization=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNzkxOTMzNDE5NSIsInRnX3VzZXJuYW1lIjoi4p61IFtvZmZsaW5lXSIsImlhdCI6MTczODY5MjA3N30.SXzZ1MZcvMp5sGESj0hBKSghhxJ3k1GTWoBUbivUe1I"
             else:  
               url = f"https://master-api-v3.vercel.app/allenplus-vimeo?url={url}&authorization=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNzkxOTMzNDE5NSIsInRnX3VzZXJuYW1lIjoi4p61IFtvZmZsaW5lXSIsImlhdCI6MTczODY5MjA3N30.SXzZ1MZcvMp5sGESj0hBKSghhxJ3k1GTWoBUbivUe1I"
            
            elif url.startswith("https://videotest.adda247.com/"):
                if url.split("/")[3] != "demo":
                    url = f'https://videotest.adda247.com/demo/{url.split("https://videotest.adda247.com/")[1]}'
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            
            name1 = links[i][0].replace("\t", "").replace(":", "").replace("/", "").replace("+", "").replace("#", "").replace("|", "").replace("@", "").replace("*", "").replace(".", "").replace("https", "").replace("http", "").strip()
            if "," in raw_text3:
                 name = f'{PRENAME} {name1[:60]}'
            else:
                 name = f'{name1[:60]}'
                                        
            if "/master.mpd" in url:
                cmd= f" yt-dlp -k --allow-unplayable-formats -f bestvideo.{quality} --fixup never {url} "
                print("counted")

            if "edge.api.brightcove.com" in url:
                bcov = 'bcov_auth=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJpYXQiOjE3MjQyMzg3OTEsImNvbiI6eyJpc0FkbWluIjpmYWxzZSwiYXVzZXIiOiJVMFZ6TkdGU2NuQlZjR3h5TkZwV09FYzBURGxOZHowOSIsImlkIjoiZEUxbmNuZFBNblJqVEROVmFWTlFWbXhRTkhoS2R6MDkiLCJmaXJzdF9uYW1lIjoiYVcxV05ITjVSemR6Vm10ak1WUlBSRkF5ZVNzM1VUMDkiLCJlbWFpbCI6Ik5Ga3hNVWhxUXpRNFJ6VlhiR0ppWTJoUk0wMVdNR0pVTlU5clJXSkRWbXRMTTBSU2FHRnhURTFTUlQwPSIsInBob25lIjoiVUhVMFZrOWFTbmQ1ZVcwd1pqUTViRzVSYVc5aGR6MDkiLCJhdmF0YXIiOiJLM1ZzY1M4elMwcDBRbmxrYms4M1JEbHZla05pVVQwOSIsInJlZmVycmFsX2NvZGUiOiJOalZFYzBkM1IyNTBSM3B3VUZWbVRtbHFRVXAwVVQwOSIsImRldmljZV90eXBlIjoiYW5kcm9pZCIsImRldmljZV92ZXJzaW9uIjoiUShBbmRyb2lkIDEwLjApIiwiZGV2aWNlX21vZGVsIjoiU2Ftc3VuZyBTTS1TOTE4QiIsInJlbW90ZV9hZGRyIjoiNTQuMjI2LjI1NS4xNjMsIDU0LjIyNi4yNTUuMTYzIn19.snDdd-PbaoC42OUhn5SJaEGxq0VzfdzO49WTmYgTx8ra_Lz66GySZykpd2SxIZCnrKR6-R10F5sUSrKATv1CDk9ruj_ltCjEkcRq8mAqAytDcEBp72-W0Z7DtGi8LdnY7Vd9Kpaf499P-y3-godolS_7ixClcYOnWxe2nSVD5C9c5HkyisrHTvf6NFAuQC_FD3TzByldbPVKK0ag1UnHRavX8MtttjshnRhv5gJs5DQWj4Ir_dkMcJ4JaVZO3z8j0OxVLjnmuaRBujT-1pavsr1CCzjTbAcBvdjUfvzEhObWfA1-Vl5Y4bUgRHhl1U-0hne4-5fF0aouyu71Y6W0eg'
                url = url.split("bcov_auth")[0]+bcov
                
            if "youtu" in url:
                ytf = f"b[height<={raw_text2}][ext=mp4]/bv[height<={raw_text2}][ext=mp4]+ba[ext=m4a]/b[ext=mp4]"
            else:
                ytf = f"b[height<={raw_text2}]/bv[height<={raw_text2}]+ba/b/bv+ba"
            
            if "jw-prod" in url:
                cmd = f'yt-dlp -o "{name}.mp4" "{url}"'

            elif "youtube.com" in url or "youtu.be" in url:
                cmd = f'yt-dlp --cookies youtube_cookies.txt -f "{ytf}" "{url}" -o "{name}".mp4'

            else:
                cmd = f'yt-dlp -f "{ytf}" "{url}" -o "{name}.mp4"'

            try:                                 
                if raw_text5 == "yes":
                    # Check the format of the link to extract video name and topic name accordingly
                    if links[i][0].startswith("("):
                        # Extract the topic name for format: (TOPIC) Video Name:URL
                        t_name = re.search(r"\((.*?)\)", links[i][0]).group(1).strip().upper()
                        v_name = re.search(r"\)\s*(.*?):", links[i][0]).group(1).strip()
                    else:
                        # Extract the topic name for format: Video Name (TOPIC):URL
                        t_name = re.search(r"\((.*?)\)", links[i][0]).group(1).strip().upper()
                        v_name = links[i][0].split("(", 1)[0].strip()
                    
                    cc = f'⋅ ─  ✨`{t_name}`✨  ─ ⋅\n\n[🎥]Vid Id : {str(count).zfill(3)}\n**Video Title :** `{v_name} [{res}p] .mkv`\n<blockquote>**Batch Name :** {b_name}</blockquote>\n\n**Extracted by➤**{CR}\n'
                    cc1 = f'⋅ ─  ✨`{t_name}`✨  ─ ⋅\n\n[📕]Pdf Id : {str(count).zfill(3)}\n**File Title :** `{v_name} .pdf`\n<blockquote>**Batch Name :** {b_name}</blockquote>\n\n**Extracted by➤**{CR}\n'
                    cczip = f'⋅ ─  ✨`{t_name}`✨  ─ ⋅\n\n[📁]Zip Id : {str(count).zfill(3)}\n**Zip Title :** `{v_name} .zip`\n<blockquote>**Batch Name :** {b_name}</blockquote>\n\n**Extracted by➤**{CR}\n' 
                    ccimg = f'⋅ ─  ✨`{t_name}`✨  ─ ⋅\n\n[🖼️]Img Id : {str(count).zfill(3)}\n**Img Title :** `{v_name} .jpg`\n<blockquote>**Batch Name :** {b_name}</blockquote>\n\n**Extracted by➤**{CR}\n'
                    cccpvod = f'⋅ ─  ✨`{t_name}`✨  ─ ⋅\n\n[🎥]Vid Id : {str(count).zfill(3)}\n**Video Title :** `{v_name} .mp4`\n<a href="{urlcpvod}">__**Click Here to Watch Stream**__</a>\n<blockquote>**Batch Name :** {b_name}</blockquote>\n\n**Extracted by➤**{CR}\n'
                    ccyt = f'⋅ ─  ✨`{t_name}`✨  ─ ⋅\n\n[🎥]Vid Id : {str(count).zfill(3)}\n**Video Title :** `{v_name} .mp4`\n<a href="{url}">__**Click Here to Watch Stream**__</a>\n<blockquote>**Batch Name :** {b_name}</blockquote>\n\n**Extracted by➤**{CR}\n'
                
                else:
                    cc = f'[🎥]Vid Id : {str(count).zfill(3)}\n**Video Title :** `{name1} [{res}p] .mkv`\n<blockquote>**Batch Name :** {b_name}</blockquote>\n\n**Extracted by➤**{CR}\n'
                    cc1 = f'[📕]Pdf Id : {str(count).zfill(3)}\n**File Title :** `{name1} .pdf`\n<blockquote>**Batch Name :** {b_name}</blockquote>\n\n**Extracted by➤**{CR}\n'
                    cczip = f'[📁]Zip Id : {str(count).zfill(3)}\n**Zip Title :** `{name1} .zip`\n<blockquote>**Batch Name :** {b_name}</blockquote>\n\n**Extracted by➤**{CR}\n' 
                    ccimg = f'[🖼️]Img Id : {str(count).zfill(3)}\n**Img Title :** `{name1} .jpg`\n<blockquote>**Batch Name :** {b_name}</blockquote>\n\n**Extracted by➤**{CR}\n'
                    cccpvod = f'[🎥]Vid Id : {str(count).zfill(3)}\n**Video Title :** `{name1} .mp4`\n<a href="{urlcpvod}">__**Click Here to Watch Stream**__</a>\n<blockquote>**Batch Name :** {b_name}</blockquote>\n\n**Extracted by➤**{CR}\n'
                    ccyt = f'[🎥]Vid Id : {str(count).zfill(3)}\n**Video Title :** `{name1} .mp4`\n<a href="{url}">__**Click Here to Watch Stream**__</a>\n<blockquote>**Batch Name :** {b_name}</blockquote>\n\n**Extracted by➤**{CR}\n'
                
                  
                if "drive" in url:
                    try:
                        ka = await helper.download(url, name)
                        copy = await bot.send_document(chat_id=channel_id,document=ka, caption=cc1)
                        count+=1
                        os.remove(ka)
                        time.sleep(1)
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        count+=1
                        continue

                elif 'pdf*' in url:
                    try:
                        pdf_key = url.split('*')[1]
                        url = url.split('*')[0]
                        pdf_enc = await helper.download_and_decrypt_pdf(url, name, pdf_key)
                        copy = await bot.send_document(chat_id=channel_id, document=pdf_enc, caption=cc1)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
                        count += 1                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
                        os.remove(pdf_enc)
                        time.sleep(1)
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        count+=1
                        continue
                  
              #  elif ".pdf*" in url:
                   # try:
                  #      url_part, key_part = url.split("*")
                      #  url = f"https://dragoapi.vercel.app/pdf/{url_part}*{key_part}"
                     #   cmd = f'yt-dlp -o "{name}.pdf" "{url}"'
                      #  download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                      #  os.system(download_cmd)
                     #   copy = await bot.send_document(chat_id=channel_id, document=f'{name}.pdf', caption=cc1)
                      #  count += 1
                     #   os.remove(f'{name}.pdf')
                  #  except FloodWait as e:
                     #   await m.reply_text(str(e))
                     #   time.sleep(e.x)
                     #   count += 1
                      #  continue 

                elif ".pdf" in url:                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
                    try:
                        if "cwmediabkt99" in url:  # if cw urls pdf is found if error then contact me with error
                            time.sleep(2)
                            cmd = f'yt-dlp -o "{name}.pdf" "https://master-api-v3.vercel.app/cw-pdf?url={url}&authorization=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNzkxOTMzNDE5NSIsInRnX3VzZXJuYW1lIjoi4p61IFtvZmZsaW5lXSIsImlhdCI6MTczODY5MjA3N30.SXzZ1MZcvMp5sGESj0hBKSghhxJ3k1GTWoBUbivUe1I"'                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 
                            download_cmd = f"{cmd} -R 25 --fragment-retries 25"                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
                            os.system(download_cmd)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
                            copy = await bot.send_document(chat_id=channel_id, document=f'{name}.pdf', caption=cc1)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
                            count += 1                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
                            os.remove(f'{name}.pdf')
                            
                        else:
                            cmd = f'yt-dlp -o "{name}.pdf" "{url}"'
                            download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                            # os.system(download_cmd)
                            # file_path= f'{name}.pdf'
                            # new_file_path = await helper.watermark_pdf(file_path, watermark_text)
                            # copy = await bot.send_document(chat_id=m.chat.id, document=new_file_path, caption=cc1)
                            os.system(download_cmd)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
                            copy = await bot.send_document(chat_id=channel_id, document=f'{name}.pdf', caption=cc1) 
                            count +=1
                            # os.remove(new_file_path)
                            os.remove(f'{name}.pdf')
                            
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        continue 

                elif ".pdf" in url:
                    try:
                        await asyncio.sleep(4)
                        url = url.replace(" ", "%20")
                        scraper = cloudscraper.create_scraper()
                        response = scraper.get(url)
                        if response.status_code == 200:
                            with open(f'{name}.pdf', 'wb') as file:
                                file.write(response.content)
                            await asyncio.sleep(4)
                            copy = await bot.send_document(chat_id=channel_id, document=f'{name}.pdf', caption=cc1)
                            count += 1
                            os.remove(f'{name}.pdf')
                        else:
                            await bot.send_message(f"Failed to download PDF: {response.status_code} {response.reason}")
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        count += 1
                        continue

                elif ".zip" in url:
                    try:
                        url = f"https://video.pablocoder.eu.org/appx-zip?url={url}"
                        BUTTONSZIP= InlineKeyboardMarkup([[InlineKeyboardButton(text="🎥 ZIP STREAM IN PLAYER", url=f"{url}")]])
                        await bot.send_photo(chat_id=channel_id, photo=photozip, caption=cczip, reply_markup=BUTTONSZIP)
                        count +=1
                    except Exception as e:
                        await m.reply_text(str(e))    
                        time.sleep(1)    
                        continue

                elif any(ext in url for ext in [".jpg", ".jpeg", ".png"]):
                    try:
                        ext = url.split('.')[-1]
                        cmd = f'yt-dlp -o "{name}.{ext}" "{url}"'
                        download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                        os.system(download_cmd)
                        copy = await bot.send_photo(chat_id=m.chat.id, photo=f'{name}.{ext}', caption=cc1)
                        count += 1
                        os.remove(f'{name}.{ext}')
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        count += 1
                        continue

               # elif "youtu" in url:
                 #   try:
                       # await bot.send_photo(chat_id=channel_id, photo=photoyt, caption=ccyt)
                      #  count +=1
                   # except Exception as e:
                      #  await m.reply_text(str(e))    
                       # time.sleep(1)    
                      #  continue

                elif 'encrypted.m' in url:  
                    remaining_links = len(links) - count
                    progress = (count / len(links)) * 100
                    #emoji_message = await show_random_emojis(message)
                    Show = f"**__Video Downloading__**\n<blockquote>{str(count).zfill(3)}) {name1}</blockquote>"
                   # Show = f"✈️ 𝐏𝐑𝐎𝐆𝐑𝐄𝐒𝐒 ✈️\n\n┠ 📈 Total Links = {len(links)}\n┠ 💥 Currently On = {str(count).zfill(3)}\n\n**📩 𝐃𝐎𝐖𝐍𝐋𝐎𝐀𝐃𝐈𝐍𝐆 📩**\n\n**🧚🏻‍♂️ Title** : {name}\n├── **Extention** : {MR}\n├── **Resolution** : {raw_text2}\n├── **Url** : `Kya karega URL dekh ke  BSDK 👻👻`\n├── **Thumbnail** : `{input6.text}`\n├── **Bot Made By** : 🅱🅴🅰🆂🆃 👑" 
                    prog = await m.reply_text(Show)  
                    res_file = await helper.download_and_decrypt_video(url, cmd, name, appxkey)  
                    filename = res_file  
                    await prog.delete(True)  
                    #await emoji_message.delete()
                    await helper.send_vid(bot, m, cc, filename, thumb, name, prog, channel_id)  
                    count += 1  
                    await asyncio.sleep(1)  
                    continue  

                elif 'drmcdni' in url or 'drm/wv' in url:
                    remaining_links = len(links) - count
                    progress = (count / len(links)) * 100
                    #emoji_message = await show_random_emojis(message)
                    Show = f"**__Video Downloading__**\n<blockquote>{str(count).zfill(3)}) {name1}</blockquote>"
                    #Show = f"𝐏𝐑𝐎𝐆𝐑𝐄𝐒𝐒 ✈️\n\n┠ 📈 Total Links = {len(links)}\n┠ 💥 Currently On = {str(count).zfill(3)}\n\n**📩 𝐃𝐎𝐖𝐍𝐋𝐎𝐀𝐃𝐈𝐍𝐆 📩**\n\n**🧚🏻‍♂️ Title** : {name}\n├── **Extention** : {MR}\n├── **Resolution** : {raw_text2}\n├── **Url** : `Kya karega URL dekh ke  BSDK 👻👻`\n├── **Thumbnail** : `{input6.text}`\n├── **Bot Made By** : 🅱🅴🅰🆂🆃 👑"
                    prog = await m.reply_text(Show)
                    res_file = await helper.decrypt_and_merge_video(mpd, keys_string, path, name, raw_text2)
                    filename = res_file
                    await prog.delete(True)
                    #await emoji_message.delete()
                    await helper.send_vid(bot, m, cc, filename, thumb, name, prog, channel_id)
                    count += 1
                    await asyncio.sleep(1)
                    continue
     
                else:
                    remaining_links = len(links) - count
                    progress = (count / len(links)) * 100
                    #emoji_message = await show_random_emojis(message)
                    Show = f"**__Video Downloading__**\n<blockquote>{str(count).zfill(3)}) {name1}</blockquote>"
                  #  Show = f"🚀𝐏𝐑𝐎𝐆𝐑𝐄𝐒𝐒 » {progress:.2f}%\n┃\n" \
                   #        f"┣🔗𝐈𝐧𝐝𝐞𝐱 » {str(count)}/{len(links)}\n┃\n" \
                        #   f"╰━🖇️𝐑𝐞𝐦𝐚𝐢𝐧𝐢𝐧𝐠 𝐋𝐢𝐧𝐤𝐬 » {remaining_links}\n\n" \
                      #     f"**⚡Dᴏᴡɴʟᴏᴀᴅ Sᴛᴀʀᴛᴇᴅ...⏳**\n\n" \
                       #    f"📚𝐓𝐢𝐭𝐥𝐞 » `{name}`\n┃\n" \
                       #    f"┣🍁𝐐𝐮𝐚𝐥𝐢𝐭𝐲 » {raw_text2}p\n┃\n" \
                        #   f'┣━🔗𝐋𝐢𝐧𝐤 » <a href="{link0}">__**Click Here to Open Link**__</a>\n┃\n' \
                         #  f'╰━━🖼️𝐓𝐡𝐮𝐦𝐛𝐧𝐚𝐢𝐥 » <a href="{raw_text6}">__**Thumb View**__</a>\n\n' \
                          # f"✦𝐁𝐨𝐭 𝐌𝐚𝐝𝐞 𝐁𝐲 ✦ `𝙎𝘼𝙄𝙉𝙄 𝘽𝙊𝙏𝙎🐦`"
                    prog = await bot.send_message(channel_id, Show, disable_web_page_preview=True)
                    res_file = await helper.download_video(url, cmd, name)
                    filename = res_file
                    await prog.delete(True)
                    #await emoji_message.delete()
                    await helper.send_vid(bot, m, cc, filename, thumb, name, prog, channel_id)
                    count += 1
                    time.sleep(1)
                
            except Exception as e:
                await bot.send_message(channel_id, f'⚠️**Downloading Failed**⚠️\n**Name** =>> `{str(count).zfill(3)} {name1}`\n**Url** =>> {link0}', disable_web_page_preview=True)
                failed_links.append(f"{name1} : {link0}")
                count += 1
                failed_count += 1
                continue

    except Exception as e:
        await m.reply_text(e)
        time.sleep(2)

    if failed_links:
     error_file_send = await m.reply_text("**📤 Sending you Failed Downloads List **")
     with open("failed_downloads.txt", "w") as f:
        for link in failed_links:
            f.write(link + "\n")
    # After writing to the file, send it
     await m.reply_document(document="failed_downloads.txt", caption=fail_cap)
     await error_file_send.delete()
     failed_links.clear()
     os.remove(f'failed_downloads.txt')

    if raw_text7 == "/d":
         success_count = len(links) - failed_count
         await bot.send_message(channel_id, f"-┈━═.•°✅ Completed ✅°•.═━┈-\n<blockquote>🎯𝙱𝚊𝚝𝚌𝚑 𝙽𝚊𝚖𝚎 » {b_name}</blockquote>\n<blockquote>🔗 Total URLs: {len(links)} \n┃   ┠🔴 Total Failed URLs: {failed_count}\n┃   ┠🟢 Total Successful URLs: {success_count}\n┃   ┃   ┠🎥 Total Video URLs: {other_count}\n┃   ┃   ┠📄 Total PDF URLs: {pdf_count}\n┃   ┃   ┠📸 Total IMAGE URLs: {img_count}</blockquote>\n")
          
    else:
         success_count = len(links) - failed_count
         await bot.send_message(channel_id, f"-┈━═.•°✅ Completed ✅°•.═━┈-\n<blockquote>🎯𝙱𝚊𝚝𝚌𝚑 𝙽𝚊𝚖𝚎 » <a href='{batch_link}'>{b_name}</a>\n</blockquote>\n<blockquote>🔗 Total URLs: {len(links)} \n┃   ┠🔴 Total Failed URLs: {failed_count}\n┃   ┠🟢 Total Successful URLs: {success_count}\n┃   ┃   ┠🎥 Total Video URLs: {other_count}\n┃   ┃   ┠📄 Total PDF URLs: {pdf_count}\n┃   ┃   ┠📸 Total IMAGE URLs: {img_count}</blockquote>\n")
         await bot.send_message(m.chat.id, f"<blockquote>✅ Your Task is completed, please check your Set Channel📱</blockquote>")

    
    #await bot.send_message(channel_id,
                          #   f"╭─────────────────────\n"
                          #   f"📚𝙱𝚊𝚝𝚌𝚑 𝙽𝚊𝚖𝚎 » <a href='{batch_link}'>{b_name}</a>\n"
                           #  f"╰─────────────────────\n"
                           #  f"`╭─────────────────────╮\n"
                          #   f"├✨𝙱𝚊𝚝𝚌𝚑 𝚂𝚞𝚖𝚖𝚊𝚛𝚢✨\n"
                           #  f"├─────────────────────\n"
                           #  f"├🔹𝙸𝚗𝚍𝚎𝚡 𝚁𝚊𝚗𝚐𝚎 » ({raw_text} ➠ {len(links)})\n"  
                          #   f"├─────────────────────\n"
                          #   f"├🔹𝙵𝚊𝚒𝚕𝚎𝚍 𝙻𝚒𝚗𝚔𝚜 » {failed_count}\n"
                          #   f"├✅𝚂𝚝𝚊𝚝𝚞𝚜 » 𝙲𝚘𝚖𝚙𝚕𝚎𝚝𝚎𝚍\n"
                           #  f"├─────────────────────\n"
                           #  f"├✦𝐁𝐨𝐭 𝐌𝐚𝐝𝐞 𝐁𝐲 ✦𝙎𝘼𝙄𝙉𝙄 𝘽𝙊𝙏𝙎\n"
                          #   f"╰─────────────────────╯\n`")


#================================================================================================================================
# Telegram channel where files will be forwarded
CHANNEL_USERNAME = "newgrp3"  # Replace with your channel username

# Function to extract names and URLs from the text file
def extract_names_and_urls(file_content):
    lines = file_content.strip().split("\n")
    data = []
    for line in lines:
        if ":" in line:
            name, url = line.split(":", 1)
            data.append((name.strip(), url.strip()))
    return data

# Function to categorize URLs
def categorize_urls(urls):
    videos = []
    pdfs = []
    others = []

    for name, url in urls:
        new_url = url
        if "media-cdn.classplusapp.com/drm/" in url or "cpvod.testbook" in url:
            new_url = f"https://dragoapi.vercel.app/video/{url}"
            videos.append((name, new_url))
        elif "/master.mpd" in url:
            vid_id = url.split("/")[-2]
            new_url = f"https://player.muftukmall.site/?id={vid_id}"
            videos.append((name, new_url))

        elif "youtube.com/embed" in url:
            yt_id = url.split("/")[-1]
            new_url = f"https://www.youtube.com/watch?v={yt_id}"
            
        elif ".m3u8" in url:
            videos.append((name, url))
        elif "pdf" in url:
            pdfs.append((name, url))
        else:
            others.append((name, url))

    return videos, pdfs, others

# Function to generate HTML file with Video.js player and download feature
def generate_html(file_name, videos, pdfs, others):
    file_name_without_extension = os.path.splitext(file_name)[0]

    video_links = "".join(f'<a href="#" onclick="playVideo(\'{url}\')">{name}</a>' for name, url in videos)
    pdf_links = "".join(f'<a href="{url}" target="_blank">{name}</a> <a href="{url}" download>📥 Download PDF</a>' for name, url in pdfs)
    other_links = "".join(f'<a href="{url}" target="_blank">{name}</a>' for name, url in others)

    html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{file_name_without_extension}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
    <link href="https://vjs.zencdn.net/8.10.0/video-js.css" rel="stylesheet" />
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: Arial, sans-serif; }}
        body {{ background: #f5f7fa; text-align: center; }}
        .header {{ background: linear-gradient(90deg, #007bff, #6610f2); color: white; padding: 15px; font-size: 24px; font-weight: bold; }}
        .subheading {{ font-size: 18px; margin-top: 10px; color: #555; font-weight: bold; }}
        .subheading a {{ background: linear-gradient(90deg, #ff416c, #ff4b2b); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-decoration: none; font-weight: bold; }}
        .container {{ display: flex; justify-content: space-around; margin: 30px auto; width: 80%; }}
        .tab {{ flex: 1; padding: 20px; background: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1); cursor: pointer; transition: 0.3s; border-radius: 10px; font-size: 20px; font-weight: bold; }}
        .tab:hover {{ background: #007bff; color: white; }}
        .content {{ display: none; margin-top: 20px; }}
        .active {{ display: block; }}
        .footer {{ margin-top: 30px; font-size: 18px; font-weight: bold; padding: 15px; background: #1c1c1c; color: white; border-radius: 10px; }}
        .footer a {{ color: #ffeb3b; text-decoration: none; font-weight: bold; }}
        .video-list, .pdf-list, .other-list {{ text-align: left; max-width: 600px; margin: auto; }}
        .video-list a, .pdf-list a, .other-list a {{ display: block; padding: 10px; background: #fff; margin: 5px 0; border-radius: 5px; text-decoration: none; color: #007bff; font-weight: bold; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); }}
        .video-list a:hover, .pdf-list a:hover, .other-list a:hover {{ background: #007bff; color: white; }}
        .search-bar {{ margin: 20px auto; width: 80%; max-width: 600px; }}
        .search-bar input {{ width: 100%; padding: 10px; border: 2px solid #007bff; border-radius: 5px; font-size: 16px; }}
        .no-results {{ color: red; font-weight: bold; margin-top: 20px; display: none; }}
        #video-player {{ display: none; margin: 20px auto; width: 80%; max-width: 800px; }}
        .download-button {{ margin-top: 10px; text-align: center; }}
        .download-button a {{ background: #007bff; color: white; padding: 10px 20px; border-radius: 5px; text-decoration: none; font-weight: bold; }}
        .download-button a:hover {{ background: #0056b3; }}
    </style>
</head>
<body>
    <div class="header">{file_name_without_extension}</div>
    <div class="subheading">📥 𝐄𝐱𝐭𝐫𝐚𝐜𝐭𝐞𝐝 𝐁𝐲 : <a href="https://t.me/+-UUAslfhnugyZjZl" target="_blank">𝙎𝘼𝙄𝙉𝙄 𝘽𝙊𝙏𝙎</a></div>

    <div class="search-bar">
        <input type="text" id="searchInput" placeholder="Search for videos, PDFs, or other resources..." oninput="filterContent()">
    </div>

    <div id="noResults" class="no-results">No results found.</div>

    <div id="video-player">
        <video id="engineer-babu-player" class="video-js vjs-default-skin" controls preload="auto" width="640" height="360">
            <p class="vjs-no-js">
                To view this video please enable JavaScript, and consider upgrading to a web browser that
                <a href="https://videojs.com/html5-video-support/" target="_blank">supports HTML5 video</a>
            </p>
        </video>
        <div class="download-button">
            <a id="download-link" href="#" download>Download Video</a>
        </div>
        <div style="text-align: center; margin-top: 10px; font-weight: bold; color: #007bff;"> Player</div>
    </div>

    <div class="container">
        <div class="tab" onclick="showContent('videos')">Videos</div>
        <div class="tab" onclick="showContent('pdfs')">PDFs</div>
        <div class="tab" onclick="showContent('others')">Others</div>
    </div>

    <div id="videos" class="content">
        <h2>All Video Lectures</h2>
        <div class="video-list">
            {video_links}
        </div>
    </div>

    <div id="pdfs" class="content">
        <h2>All PDFs</h2>
        <div class="pdf-list">
            {pdf_links}
        </div>
    </div>

    <div id="others" class="content">
        <h2>Other Resources</h2>
        <div class="other-list">
            {other_links}
        </div>
    </div>

    <div class="footer">📥 𝐄𝐱𝐭𝐫𝐚𝐜𝐭𝐞𝐝 𝐁𝐲 : <a href="https://t.me/+-UUAslfhnugyZjZl" target="_blank">𝙎𝘼𝙄𝙉𝙄 𝘽𝙊𝙏𝙎</a></div>

    <script src="https://vjs.zencdn.net/8.10.0/video.min.js"></script>
    <script>
        const player = videojs('SAINI_BOTS_PLAYER', {{
            controls: true,
            autoplay: false,
            preload: 'auto',
            fluid: true,
        }});

        function playVideo(url) {{
            if (url.includes('.m3u8')) {{
                document.getElementById('video-player').style.display = 'block';
                player.src({{ src: url, type: 'application/x-mpegURL' }});
                player.play().catch(() => {{
                    window.open(url, '_blank');
                }});
                document.getElementById('download-link').href = url;
            }} else {{
                window.open(url, '_blank');
            }}
        }}

        function showContent(tabName) {{
            const contents = document.querySelectorAll('.content');
            contents.forEach(content => {{
                content.style.display = 'none';
            }});
            const selectedContent = document.getElementById(tabName);
            if (selectedContent) {{
                selectedContent.style.display = 'block';
            }}
            filterContent();
        }}

        function filterContent() {{
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            const categories = ['videos', 'pdfs', 'others'];
            let hasResults = false;

            categories.forEach(category => {{
                const items = document.querySelectorAll(`#${{category}} .${{category}}-list a`);
                let categoryHasResults = false;

                items.forEach(item => {{
                    const itemText = item.textContent.toLowerCase();
                    if (itemText.includes(searchTerm)) {{
                        item.style.display = 'block';
                        categoryHasResults = true;
                        hasResults = true;
                    }} else {{
                        item.style.display = 'none';
                    }}
                }});

                const categoryHeading = document.querySelector(`#${{category}} h2`);
                if (categoryHeading) {{
                    categoryHeading.style.display = categoryHasResults ? 'block' : 'none';
                }}
            }});

            const noResultsMessage = document.getElementById('noResults');
            if (noResultsMessage) {{
                noResultsMessage.style.display = hasResults ? 'none' : 'block';
            }}
        }}

        document.addEventListener('DOMContentLoaded', () => {{
            showContent('videos');
        }});
    </script>
</body>
</html>
    """
    return html_template

@bot.on_message(filters.command(["t2h"]) )
async def txt_handler(bot: Client, m: Message):
    editable=await m.reply_text(f"𝐖𝐞𝐥𝐜𝐨𝐦𝐞! 𝐏𝐥𝐞𝐚𝐬𝐞 𝐮𝐩𝐥𝐨𝐚𝐝 𝐚 .𝐭𝐱𝐭 𝐟𝐢𝐥𝐞 𝐜𝐨𝐧𝐭𝐚𝐢𝐧𝐢𝐧𝐠 𝐔𝐑𝐋𝐬.")
    Message = await bot.listen(editable.chat.id)
    
    if not hasattr(message, "document") or not message.document:
        await bot.send_message(chat_id=m.chat.id, text="Please upload a file.")
        return

    if not message.document.file_name.endswith(".txt"):
        await bot.send_message(chat_id=m.chat.id, text="Please upload a .txt file.")
        return

    # Download the file
    file_path = await message.download()
    file_name = message.document.file_name

    # Read the file content
    with open(file_path, "r") as f:
        file_content = f.read()

    # Extract names and URLs
    urls = extract_names_and_urls(file_content)

    # Categorize URLs
    videos, pdfs, others = categorize_urls(urls)

    # Generate HTML
    html_content = generate_html(file_name, videos, pdfs, others)
    html_file_path = file_path.replace(".txt", ".html")
    with open(html_file_path, "w") as f:
        f.write(html_content)

    # Send the HTML file to the user
    await bot.send_document(chat_id=m.chat.id, document=html_file_path, caption="✅ 𝐒𝐮𝐜𝐜𝐞𝐬𝐬𝐟𝐮𝐥𝐥𝐲 𝐃𝐨𝐧𝐞!\n\n📥 𝐄𝐱𝐭𝐫𝐚𝐜𝐭𝐞𝐝 𝐁𝐲 : 𝙎𝘼𝙄𝙉𝙄 𝘽𝙊𝙏𝙎")

    # Forward the .txt file to the channel
  #  await client.send_document(chat_id=CHANNEL_USERNAME, document=file_path)

    # Clean up files
    os.remove(file_path)
    os.remove(html_file_path)

#================================================================================================================================
bot.run()
if __name__ == "__main__":
    asyncio.run(main())
