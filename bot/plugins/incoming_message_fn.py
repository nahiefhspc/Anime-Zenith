import logging
import anitopy
import datetime

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
LOGGER = logging.getLogger(__name__)

import os
import time
import asyncio
import json
from bot.localisation import Localisation
from bot import (
    DOWNLOAD_LOCATION,
    AUTH_USERS,
    LOG_CHANNEL,
    UPDATES_CHANNEL,
    SESSION_NAME,
    data,
    app
)
from bot.helper_funcs.ffmpeg import (
    convert_video,
    media_info,
    take_screen_shot
)
from bot.helper_funcs.display_progress import (
    progress_for_pyrogram,
    TimeFormatter,
    humanbytes
)
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant, UsernameNotOccupied, ChatAdminRequired, PeerIdInvalid

os.system("wget https://telegra.ph/file/059d8942b7c02750c01ab.jpg -O thumb.jpg")

CURRENT_PROCESSES = {}
CHAT_FLOOD = {}
broadcast_ids = {}
bot = app

async def incoming_start_message_f(bot, update):
    await bot.send_message(
        chat_id=update.chat.id,
        text=Localisation.START_TEXT,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton('Channel', url='https://t.me/AnimeSpectrum')]]
        ),
        reply_to_message_id=update.id,
    )

async def incoming_compress_message_f(bot, update):  # Added 'bot' parameter
    isAuto = True
    d_start = time.time()
    c_start = time.time()
    u_start = time.time()
    status = os.path.join(DOWNLOAD_LOCATION, "status.json")
    sent_message = await bot.send_message(
        chat_id=update.chat.id,
        text=Localisation.DOWNLOAD_START,
        reply_to_message_id=update.id
    )
    chat_id = LOG_CHANNEL
    utc_now = datetime.datetime.utcnow()
    ist_now = utc_now + datetime.timedelta(minutes=30, hours=5)
    ist = ist_now.strftime("%d/%m/%Y, %H:%M:%S")
    bst_now = utc_now + datetime.timedelta(minutes=00, hours=6)
    bst = bst_now.strftime("%d/%m/%Y, %H:%M:%S")
    now = f"\n{ist} (GMT+05:30)`\n`{bst} (GMT+06:00)"
    download_start = await bot.send_message(chat_id, f"**Bot Become Busy Now !!** \n\nDownload Started at `{now}`")

    try:
        with open(status, 'w') as f:
            json.dump({'running': True, 'message': sent_message.id}, f, indent=2)
        video = await bot.download_media(
            message=update,
            progress=progress_for_pyrogram,
            progress_args=(bot, Localisation.DOWNLOAD_START, sent_message, d_start)
        )
        saved_file_path = video
        LOGGER.info(f"Downloaded file: {saved_file_path}")
        if not video or not os.path.exists(saved_file_path):
            await sent_message.edit_text(text="Download failed or file not found")
            await bot.send_message(chat_id, f"**Download Failed, Bot is Free Now !!** \n\nProcess Done at `{now}`")
            await download_start.delete()
            return
    except Exception as e:
        LOGGER.error(f"Download error: {str(e)}")
        await sent_message.edit_text(text=f"Download error: {str(e)}")
        await bot.send_message(chat_id, f"**Download Failed, Bot is Free Now !!** \n\nProcess Done at `{now}`")
        await download_start.delete()
        return

    await sent_message.edit_text(text=Localisation.SAVED_RECVD_DOC_FILE)

    duration, bitrate = await media_info(saved_file_path)
    if duration is None or bitrate is None:
        await sent_message.edit_text(text="❌ Getting video metadata failed ❌")
        await bot.send_message(chat_id, f"**Metadata Failed, Bot is Free Now !!** \n\nProcess Done at `{now}`")
        await download_start.delete()
        return

    thumb_image_path = await take_screen_shot(saved_file_path, os.path.dirname(saved_file_path), duration / 2)
    if not thumb_image_path or not os.path.exists(thumb_image_path):
        LOGGER.warning("Thumbnail generation failed, using default")
        thumb_image_path = "thumb.jpg" if os.path.exists("thumb.jpg") else None

    await download_start.delete()
    compress_start = await bot.send_message(chat_id, f"**Compressing Video ...** \n\nProcess Started at `{now}`")
    await sent_message.edit_text(text=Localisation.COMPRESS_START)
    c_start = time.time()
    o = await convert_video(video, DOWNLOAD_LOCATION, duration, bot, sent_message, compress_start)
    compressed_time = TimeFormatter((time.time() - c_start) * 1000)
    LOGGER.info(f"Compressed file: {o}")

    if o == 'stopped':
        return
    if not o or not os.path.exists(o):
        await sent_message.edit_text(text="⚠️ Compression failed or file not found ⚠️")
        await bot.send_message(chat_id, f"**Compression Failed, Bot is Free Now !!** \n\nProcess Done at `{now}`")
        await compress_start.delete()
        return

    await compress_start.delete()
    upload_start = await bot.send_message(chat_id, f"**Uploading Video ...** \n\nProcess Started at `{now}`")
    await sent_message.edit_text(text=Localisation.UPLOAD_START)
    u_start = time.time()

    try:
        anime_title_data = anitopy.parse(update.message.text)
        anime_name = anime_title_data.get('anime_title', 'Unknown Anime')
        episode_number = anime_title_data.get('episode_number', '??')
        season_number = anime_title_data.get('season_number', '??')
        caption = f"{anime_name}, S{season_number}E{episode_number}, Anime Zenith"

        upload = await bot.send_document(
            chat_id=update.chat.id,
            document=o,
            caption=caption,
            force_document=True,
            thumb=thumb_image_path,
            reply_to_message_id=update.id,
            progress=progress_for_pyrogram,
            progress_args=(bot, Localisation.UPLOAD_START, sent_message, u_start)
        )

        if not upload:
            raise ValueError("Upload returned None")

        uploaded_time = TimeFormatter((time.time() - u_start) * 1000)
        await sent_message.delete()
        await upload_start.delete()
        await bot.send_message(chat_id, f"**Upload Done, Bot is Free Now !!** \n\nProcess Done at `{now}`")
        LOGGER.info(f"Uploaded with caption: {upload.caption}")
        await upload.edit_caption(caption=f"{caption} | Uploaded in {uploaded_time}")

    except Exception as e:
        LOGGER.error(f"Upload error: {str(e)}")
        await sent_message.edit_text(text=f"⚠️ Upload failed: {str(e)} ⚠️")
        await bot.send_message(chat_id, f"**Upload Failed, Bot is Free Now !!** \n\nProcess Done at `{now}`")
        await upload_start.delete()
        if os.path.exists(o):
            os.remove(o)
        return

    # Cleanup
    if os.path.exists(saved_file_path):
        os.remove(saved_file_path)
    if os.path.exists(o):
        os.remove(o)

async def incoming_cancel_message_f(bot, update):
    if update.from_user.id not in AUTH_USERS:
        try:
            await update.message.delete()
        except:
            pass
        return

    status = os.path.join(DOWNLOAD_LOCATION, "status.json")
    if os.path.exists(status):
        inline_keyboard = [[
            InlineKeyboardButton("Yes 🚫", callback_data="fuckingdo"),
            InlineKeyboardButton("No 🤗", callback_data="fuckoff")
        ]]
        reply_markup = InlineKeyboardMarkup(inline_keyboard)
        await update.reply_text("Are you sure? 🚫 This will stop the compression!", reply_markup=reply_markup, quote=True)
    else:
        await bot.send_message(
            chat_id=update.chat.id,
            text="No active compression exists",
            reply_to_message_id=update.id
)
