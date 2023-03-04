import asyncio
import logging
import os
import pathlib

import aiogram.utils.markdown as md
import asyncpg
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import Message
from aiogram.contrib.fsm_storage.memory import MemoryStorage
# from aioredis import Redis

from bot.command import media_path_1, media_path_2, media_path_3, video_path_1, video_path_2, Bottons


def setup_env():
    from dotenv import load_dotenv
    dotenv_path = os.path.join(os.path.dirname(__file__), '../.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
setup_env()

API_TOKEN = os.getenv('BOT_TOKEN')
ID_USER = int(os.getenv('user_id_'))

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())


# redis = Redis()
# storage = RedisStorage(redis)
# For example use simple BotClient, but you can use other AiohttpClient.


async def on_startup(dp):
    try:
        global db_pool
        db_pool = await asyncpg.create_pool(

            port=int(os.getenv('POSTGRES_PORT') or 0),
            host=os.getenv('POSTGRES_HOST'),
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD'),
            database=os.getenv('POSTGRES_DB')
        )

        async with db_pool.acquire() as con:
            await con.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    active BOOLEAN DEFAULT TRUE,
                    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_update_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            await con.execute('''
                DROP TRIGGER IF EXISTS trigger_update_last_update_date ON users;
            ''')
            await con.execute('''
                CREATE OR REPLACE FUNCTION update_last_update_date()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.last_update_date = NOW();
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            ''')
            await con.execute('''
                CREATE TRIGGER trigger_update_last_update_date
                BEFORE UPDATE ON users
                FOR EACH ROW
                EXECUTE FUNCTION update_last_update_date()
            ''')



    except Exception as e:
        logging.exception("Failed to connect to database")
        await asyncio.sleep(5)





    async def delete_inactive_users():
        inactive_period_days = 30  # Define the inactive period in days
        async with db_pool.acquire() as con:
            await con.execute(
                'DELETE FROM users WHERE active = $1 AND last_update_date < NOW() - INTERVAL \'{} days\''.format(
                    inactive_period_days), True)
    async def delete_inactive_users_task():
            while True:
                await delete_inactive_users()
                await asyncio.sleep(20)  # Run the task once a day


# Start the background task to delete inactive users
    asyncio.create_task(delete_inactive_users_task())

@dp.message_handler(commands='start')
async def cmd_start(message: types.Message):
    """
    Conversation's entry point
    """
    user_id = message.from_user.id
    async with db_pool.acquire() as con:
        await con.execute('INSERT INTO users (user_id) SELECT $1 WHERE NOT EXISTS (SELECT 1 FROM users WHERE user_id = $1)', user_id)

        # The rest of your handler code goes here

    # Create a button that can be used to continue the conversation
    inline_keyboard = types.InlineKeyboardMarkup(row_width=2)
    inline_keyboard.add(types.InlineKeyboardButton("Далее", callback_data="continue_0"))

    # Send the photo or video along with the button

    await bot.send_photo(chat_id=message.from_user.id, photo=open(media_path_1, 'rb'), caption=Bottons.button_0_photo,
                         reply_markup=inline_keyboard)


@dp.message_handler(commands=['sendall'])
async def start(message: types.Message):
    if message.chat.type == 'private':
        if message.from_user.id == ID_USER:
            text = message.text[9:]

            async with db_pool.acquire() as conn:
                active_count = await conn.fetchval('SELECT COUNT(*) FROM users WHERE active = $1', True)

                async with conn.transaction():
                    # Get all users from the database
                    rows = await conn.fetch('SELECT user_id, active FROM users')

                    for row in rows:
                        try:
                            await bot.send_message(row[0], text)
                            if not row[1]:
                                # If the user was not active, set them as active
                                await conn.execute('UPDATE users SET active = $1 WHERE user_id = $2', True, row[0])
                        except:
                            # If there was an error sending the message, set the user as inactive
                            await conn.execute('UPDATE users SET active = $1 WHERE user_id = $2', False, row[0])

            await bot.send_message(message.from_user.id, f'Успешная рассылка для {active_count} пользователей')
@dp.callback_query_handler(lambda callback_query: callback_query.data and callback_query.data.startswith("continue_"))
async def process_callback_continue(callback_query: types.CallbackQuery):
    if callback_query.data is None:
        return
    """
    Send the next message in the conversation
      """
    message_num = int(callback_query.data.split("_")[1])
    messages = [Bottons.button_1_video, Bottons.button_2_video, Bottons.button_3_photo, Bottons.button_4_only_message,
                Bottons.button_5_photo]
    if message_num >= len(messages):
        # End the conversation if all messages have been sent
        return
    #
    #     # Create a button that can be used to continue the conversation
    inline_keyboard = types.InlineKeyboardMarkup(row_width=2)
    inline_keyboard.add(types.InlineKeyboardButton("Далее", callback_data=f"continue_{message_num + 1}"))

    # ====================== Send messages==================================

    if message_num == 1:
        await bot.send_video(chat_id=callback_query.from_user.id, video=open(video_path_2, 'rb'),  # Third message
                             caption=messages[message_num], reply_markup=inline_keyboard)
    elif message_num == 2:
        await bot.send_photo(chat_id=callback_query.from_user.id, photo=open(media_path_2, 'rb'),  # Sixth message
                             caption=messages[message_num], reply_markup=inline_keyboard)
        # Send the rest of the messages with photos
    elif message_num == 3:
        await bot.send_message(chat_id=callback_query.from_user.id,  # Fourth message
                               text=messages[message_num], reply_markup=inline_keyboard)
    elif message_num == 4:
        await bot.send_photo(chat_id=callback_query.from_user.id, photo=open(media_path_3, 'rb'),  # Fifth message
                             caption=messages[message_num])
    else:
        await bot.send_video(chat_id=callback_query.from_user.id, video=open(video_path_1, 'rb'),  # Second message
                             caption=messages[message_num], reply_markup=inline_keyboard)

    await asyncio.sleep(1)  # Introduse a 1 second delay

    # ====================== Pooling bot===========================
logger = logging.getLogger(__name__)
def start_bot():
    try:

        executor.start_polling(dp, on_startup=on_startup)
        logger.info('Bot started')
    except (KeyboardInterrupt, SystemExit):
        logger.info('Bot stopped')

if __name__ == '__main__':
    start_bot()