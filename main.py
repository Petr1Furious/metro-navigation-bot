import asyncio

from telebot.async_telebot import AsyncTeleBot
from telebot import types
from sqlalchemy import create_engine
from enum import Enum
from Metro import metro


class State(Enum):
    NOTHING = 0
    SELECT_DEPARTURE = 1
    SELECT_DESTINATION = 2


metro = metro.Metro()

db_string = 'postgresql://username:secret@db:5432/database'
db = create_engine(db_string)

bot = AsyncTeleBot('5517614291:AAGXI0FzZccGcq3aeYFZUoK46mA9L2yCH8M')

client_state = {}
selected_stations = {}


@bot.message_handler(commands=['start', 'help'])
async def help_message(message):
    markup = types.ReplyKeyboardMarkup()
    markup.add(types.KeyboardButton(text='/plot'))
    markup.add(types.KeyboardButton(text='/save'),
               types.KeyboardButton(text='/list'),
               types.KeyboardButton(text='/remove'))

    with open('Long Messages/help_menu.txt', 'r') as help_menu:
        await bot.send_message(message.from_user.id, help_menu.read(), reply_markup=markup)


@bot.message_handler(commands=['plot'])
async def plot_route(message):
    msg = await bot.send_message(message.from_user.id, 'Enter departure station name (both Russian and English '
                                                       'languages are supported).')
    client_state[message.from_user.id] = State.SELECT_DEPARTURE


@bot.message_handler(commands=['cancel'])
async def cancel_query(message):
    client_state[message.from_user.id] = State.NOTHING
    await bot.send_message(message.from_user.id, 'Cancelled current query. Type /start to start.')


async def handle_station_name(message):
    if metro.get_station(message.text) is not None:
        selected_stations[message.from_user.id].append(message.text)
        return True
    else:
        similar_station_names = metro.get_similar_station_names(message.text)
        if len(similar_station_names) != 0:
            markup = types.ReplyKeyboardMarkup()
            for name in similar_station_names:
                markup.add(types.KeyboardButton(text=name))
            await bot.send_message(message.from_user.id, 'Did you mean:\n' + '\n'.join(similar_station_names),
                                   reply_markup=markup)
        else:
            await bot.send_message(message.from_user.id, 'No station with a similar name found.')
        return False


@bot.message_handler(content_types=['text'])
async def get_text_message(message):
    if client_state[message.from_user.id] == State.NOTHING:
        await bot.send_message(message.from_user.id, 'Unrecognized command. Type /start to start.')

    if client_state[message.from_user.id] == State.SELECT_DEPARTURE:
        selected_stations[message.from_user.id] = []
        if await handle_station_name(message):
            await bot.send_message(message.from_user.id, 'Enter destination station name.')
            client_state[message.from_user.id] = State.SELECT_DESTINATION

    elif client_state[message.from_user.id] == State.SELECT_DESTINATION:
        if await handle_station_name(message):
            await bot.send_message(message.from_user.id, metro.plot_route(
                selected_stations[message.from_user.id][0],
                selected_stations[message.from_user.id][1]
            ))
            client_state[message.from_user.id] = State.NOTHING


asyncio.run(bot.polling(none_stop=True, interval=0))
