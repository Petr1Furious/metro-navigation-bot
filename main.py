import asyncio

from telebot.async_telebot import AsyncTeleBot
from telebot import types
from sqlalchemy import create_engine
from enum import Enum
from Metro import metro


class State(Enum):
    DEFAULT = 0
    SELECT_DEPARTURE = 1
    SELECT_DESTINATION = 2
    CREATE_ALIAS_NAME = 3
    CREATE_ALIAS_STATION = 4
    REMOVE_ALIAS_NAME = 5


metro = metro.Metro()

db_string = 'postgresql://username:secret@db:5432/database'
db = create_engine(db_string)

bot = AsyncTeleBot('5517614291:AAGXI0FzZccGcq3aeYFZUoK46mA9L2yCH8M')

client_state = {}
selected_values = {}

cancel_markup = types.ReplyKeyboardMarkup()
cancel_markup.add('/cancel')


@bot.message_handler(commands=['start', 'help'])
async def help_message(message):
    db.execute('CREATE TABLE IF NOT EXISTS T{} (alias TEXT, station_name TEXT)'.format(message.from_user.id))

    client_state[message.from_user.id] = State.DEFAULT

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
                                                       'languages are supported).', reply_markup=cancel_markup)
    client_state[message.from_user.id] = State.SELECT_DEPARTURE


@bot.message_handler(commands=['cancel'])
async def cancel_query(message):
    client_state[message.from_user.id] = State.DEFAULT
    await bot.send_message(message.from_user.id, 'Cancelled current query.')
    await help_message(message)


@bot.message_handler(commands=['save'])
async def save_alias(message):
    client_state[message.from_user.id] = State.CREATE_ALIAS_NAME
    await bot.send_message(message.from_user.id, 'Enter alias name to save.', reply_markup=cancel_markup)


@bot.message_handler(commands=['remove'])
async def remove_alias(message):
    client_state[message.from_user.id] = State.REMOVE_ALIAS_NAME
    await bot.send_message(message.from_user.id, 'Enter alias name to remove.', reply_markup=cancel_markup)


def get_aliases(user_id):
    result = db.execute("SELECT * FROM T{}".format(user_id))

    result_aliases = {}
    for (alias, station_name) in result:
        result_aliases[alias] = station_name

    return result_aliases


@bot.message_handler(commands=['list'])
async def list_alias(message):
    aliases = ''
    for (alias, station) in get_aliases(message.from_user.id).items():
        aliases += alias + ' : ' + station + '\n'

    if aliases == '':
        aliases = 'There are no saved aliases yet.'
    else:
        aliases = 'Saved aliases:\n' + aliases

    await bot.send_message(message.from_user.id, aliases)


async def handle_station_name(message):
    if metro.get_station(message.text) is not None:
        selected_values[message.from_user.id].append(message.text)
        return True
    elif message.text in get_aliases(message.from_user.id).keys():
        selected_values[message.from_user.id].append(get_aliases(message.from_user.id)[message.text])
        return True
    else:
        similar_station_names = metro.get_similar_station_names(message.text, get_aliases(message.from_user.id))
        if len(similar_station_names) != 0:
            markup = types.ReplyKeyboardMarkup()
            for name in similar_station_names:
                markup.add(types.KeyboardButton(text=name))
            await bot.send_message(message.from_user.id, 'Did you mean:\n' + '\n'.join(similar_station_names),
                                   reply_markup=markup)
        else:
            await bot.send_message(message.from_user.id, 'No station with a similar name found.',
                                   reply_markup=cancel_markup)
        return False


@bot.message_handler(content_types=['text'])
async def get_text_message(message):
    if client_state[message.from_user.id] == State.DEFAULT:
        await bot.send_message(message.from_user.id, 'Unrecognized command. Type /start to start.')

    if client_state[message.from_user.id] == State.SELECT_DEPARTURE:
        selected_values[message.from_user.id] = []
        if await handle_station_name(message):
            await bot.send_message(message.from_user.id, 'Enter destination station name.',
                                   reply_markup=cancel_markup)
            client_state[message.from_user.id] = State.SELECT_DESTINATION

    elif client_state[message.from_user.id] == State.SELECT_DESTINATION:
        if await handle_station_name(message):
            await bot.send_message(message.from_user.id, metro.plot_route(
                selected_values[message.from_user.id][0],
                selected_values[message.from_user.id][1]
            ), parse_mode='Markdown')
            await help_message(message)

    elif client_state[message.from_user.id] == State.CREATE_ALIAS_NAME:
        selected_values[message.from_user.id] = [message.text]
        await bot.send_message(message.from_user.id, 'Enter alias station name.',
                               reply_markup=cancel_markup)
        client_state[message.from_user.id] = State.CREATE_ALIAS_STATION

    elif client_state[message.from_user.id] == State.CREATE_ALIAS_STATION:
        if await handle_station_name(message):
            db.execute("INSERT INTO T{} (alias, station_name) VALUES ('{}', '{}')"
                       .format(message.from_user.id, selected_values[message.from_user.id][0],
                               metro.get_station(message.text).get_full_name()))
            await bot.send_message(message.from_user.id, 'Successfully added new alias.')
            await help_message(message)

    elif client_state[message.from_user.id] == State.REMOVE_ALIAS_NAME:
        db.execute("DELETE FROM T{} WHERE alias = '{}'".format(message.from_user.id, message.text))
        await bot.send_message(message.from_user.id, 'Successfully removed the alias.')
        await help_message(message)


asyncio.run(bot.polling(none_stop=True, interval=0))
