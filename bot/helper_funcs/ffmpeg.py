import logging
logging.basicConfig(
    level=logging.DEBUG, 
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
LOGGER = logging.getLogger(__name__)

import asyncio
import os
import time
import re
import json
import subprocess
import math
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.helper_funcs.display_progress import TimeFormatter
from bot.localisation import Localisation
from bot import (
    FINISHED_PROGRESS_STR,
    UN_FINISHED_PROGRESS_STR,
    DOWNLOAD_LOCATION,
    crf,
    resolution,
    audio_b,
    preset,
    codec,
    name,
    acodec,
    size,
    metadata,
    metadata1,
    metadata2,
    pid_list
)

async def convert_video(video_file, output_directory, total_time, bot, message, chan_msg):
    kk = video_file.split("/")[-1]
    aa = kk.split(".")[-1]
    out_put_file_name = kk.replace(f".{aa}", "[HACKHEIST].mkv")
    progress = os.path.join(output_directory, "progress.txt")

    # Reset global lists to avoid appending indefinitely
    crf.clear(); crf.append("24")
    codec.clear(); codec.append("libx264")
    resolution.clear(); resolution.append("1280x720")
    preset.clear(); preset.append("veryfast")
    audio_b.clear(); audio_b.append("32k")
    acodec.clear(); acodec.append("libopus")
    name.clear(); name.append("HACKHEIST")
    metadata.clear(); metadata.append("HACKHEIST")
    metadata1.clear(); metadata1.append("HACKHEIST")
    metadata2.clear(); metadata2.append("HACKHEIST")
    size.clear(); size.append("15")

    # Use a list for FFmpeg command to avoid shell escaping issues
    file_genertor_command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "quiet",
        "-progress", progress,
        "-i", video_file,
        "-metadata", f"title={metadata[0]}",
        "-c:v", codec[0],
        "-map", "0",
        "-crf", crf[0],
        "-c:s", "copy",
        "-pix_fmt", "yuv420p",
        "-s", resolution[0],
        "-b:v", "32k",
        "-c:a", acodec[0],
        "-b:a", audio_b[0],
        "-preset", preset[0],
        "-metadata:s:a", f"title={metadata1[0]}",
        "-metadata:s:s", f"title={metadata2[0]}",
        "-vf", f"drawtext=fontfile=font.ttf:fontsize={size[0]}:fontcolor=white:bordercolor=black@0.50:x=w-tw-10:y=10:box=1:boxcolor=black@0.5:boxborderw=6:text={name[0]}",
        out_put_file_name,
        "-y"
    ]

    COMPRESSION_START_TIME = time.time()
    process = await asyncio.create_subprocess_exec(
        *file_genertor_command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    LOGGER.info(f"ffmpeg_process: {process.pid}")
    pid_list.insert(0, process.pid)
    status = os.path.join(output_directory, "status.json")
    with open(status, 'r+') as f:
        statusMsg = json.load(f)
        statusMsg['pid'] = process.pid
        statusMsg['message'] = message.id
        f.seek(0)
        json.dump(statusMsg, f, indent=2)

    while process.returncode is None:
        await asyncio.sleep(3)
        try:
            with open(progress, 'r') as file:
                text = file.read()
                frame = re.findall("frame=(\d+)", text)
                time_in_us = re.findall("out_time_ms=(\d+)", text)
                progress_status = re.findall("progress=(\w+)", text)
                speed = re.findall("speed=(\d+\.?\d*)", text)

                frame = int(frame[-1]) if frame else 1
                speed = float(speed[-1]) if speed else 1.0
                time_in_us = int(time_in_us[-1]) if time_in_us else 1
                if progress_status and progress_status[-1] == "end":
                    LOGGER.info("Encoding completed")
                    break

                elapsed_time = time_in_us / 1000000
                difference = math.floor((total_time - elapsed_time) / speed)
                ETA = TimeFormatter(difference * 1000) if difference > 0 else "-"
                percentage = math.floor(elapsed_time * 100 / total_time)

                progress_str = "💦 <b>ᴘʀᴏᴄᴇssɪɴɢ:</b> {0}%\n[{1}{2}]".format(
                    round(percentage, 2),
                    ''.join([FINISHED_PROGRESS_STR for _ in range(math.floor(percentage / 10))]),
                    ''.join([UN_FINISHED_PROGRESS_STR for _ in range(10 - math.floor(percentage / 10))])
                )
                stats = f'💥 <b>ᴇɴᴄᴏᴅɪɴɢ ɪɴ ᴘʀᴏɢʀᴇss</b>\n\n' \
                        f'🌄 <b>ᴛɪᴍᴇ ʟᴇғᴛ:</b> {ETA}\n\n' \
                        f'{progress_str}\n'

                await message.edit_text(
                    text=stats,
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton('❌ ᴄᴀɴᴄᴇʟ ❌', callback_data='fuckingdo')]]
                    )
                )
        except FileNotFoundError:
            LOGGER.warning("Progress file not found, continuing...")
            continue

    stdout, stderr = await process.communicate()
    e_response = stderr.decode().strip()
    t_response = stdout.decode().strip()
    LOGGER.info(f"FFmpeg stderr: {e_response}")
    LOGGER.info(f"FFmpeg stdout: {t_response}")

    del pid_list[0]
    if process.returncode != 0:
        await message.edit_text(f"Encoding failed: {e_response}\n\n**ERROR** Contact @ninja_naruto_sai_2")
        if os.path.exists(video_file):
            os.remove(video_file)
        if os.path.exists(out_put_file_name):
            os.remove(out_put_file_name)
        return None

    if os.path.exists(out_put_file_name):
        return out_put_file_name
    return None

async def media_info(saved_file_path):
    process = subprocess.Popen(
        ['ffmpeg', "-hide_banner", '-i', saved_file_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    stdout, _ = process.communicate()
    output = stdout.decode().strip()
    duration = re.search("Duration:\s*(\d*):(\d*):(\d+\.?\d*)[\s\w*$]", output)
    bitrates = re.search("bitrate:\s*(\d+)[\s\w*$]", output)

    if duration:
        hours = int(duration.group(1))
        minutes = int(duration.group(2))
        seconds = math.floor(float(duration.group(3)))
        total_seconds = (hours * 60 * 60) + (minutes * 60) + seconds
    else:
        total_seconds = None
    bitrate = bitrates.group(1) if bitrates else None
    return total_seconds, bitrate

async def take_screen_shot(video_file, output_directory, ttl):
    out_put_file_name = os.path.join(output_directory, f"{time.time()}.jpg")
    if video_file.upper().endswith(("MKV", "MP4", "WEBM")):
        file_genertor_command = [
            "ffmpeg",
            "-ss", str(ttl),
            "-i", video_file,
            "-vframes", "1",
            out_put_file_name
        ]
        process = await asyncio.create_subprocess_exec(
            *file_genertor_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        e_response = stderr.decode().strip()
        t_response = stdout.decode().strip()
        LOGGER.info(f"Screenshot stderr: {e_response}")
        LOGGER.info(f"Screenshot stdout: {t_response}")

    return out_put_file_name if os.path.exists(out_put_file_name) else None
