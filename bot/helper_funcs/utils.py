# the logging things
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
LOGGER = logging.getLogger(__name__)

import os
from bot import data, bot  # Import bot from bot module
from bot.plugins.incoming_message_fn import incoming_compress_message_f
from pyrogram.types import Message

def checkKey(dict, key):
    if key in dict.keys():
        return True
    else:
        return False

async def on_task_complete():
    del data[0]
    if len(data) > 0:
        await add_task(data[0])

async def add_task(message: Message):
    try:
        os.system('rm -rf /app/downloads/*')
        await incoming_compress_message_f(bot, message)  # Pass both bot and message
    except Exception as e:
        LOGGER.info(f"Error in add_task: {e}")
    await on_task_complete()
