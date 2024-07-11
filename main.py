import logging

import telebot
from tokens import bot as botTokens

from locLibs import dbFunc

# setup logger
botLogger = logging.getLogger('bot')
handler = logging.FileHandler('log/bot.log', mode='w')
formatter = logging.Formatter('[%(asctime)s](%(name)s)%(levelname)s:%(message)s', '%H:%M:%S')
handler.setFormatter(formatter)
botLogger.addHandler(handler)
botLogger.setLevel(logging.DEBUG)

bot = telebot.TeleBot(botTokens.token)


def getRelpyFromAdmin(reply, stopReg):
    msg = yield reply, stopReg
    while bot.get_chat_member(msg.chat.id, msg.from_user.id).status not in ['administrator', 'creator']:
        botLogger.debug(bot.get_chat_member(msg.chat.id, msg.from_user.id))
        reply = bot.send_message(msg.chat.id, 'you are not admin..')
        msg = yield reply, False
    return msg


#  registration functions
#  -reg point functions
def regPointGen(msg: telebot.types.Message):
    cityKeyboard = telebot.types.ReplyKeyboardMarkup()
    cityList = dbFunc.getCityList()

    for city in cityList:
        cityKeyboard.add(city)

    reply = bot.send_message(msg.chat.id, 'welcome group, ask about city', reply_markup=cityKeyboard)
    msg: telebot.types.Message = yield from getRelpyFromAdmin(reply, False)
    pointCity = msg.text

    while pointCity not in cityList:
        reply = bot.send_message(msg.chat.id, 'incorrect city')  # TODO is reply keyboard removed
        msg = yield from getRelpyFromAdmin(reply, False)
        pointCity = msg.text

    reply = bot.send_message(msg.chat.id, 'ask about name say about /rename',
                             reply_markup=telebot.types.ReplyKeyboardRemove())
    msg = yield from getRelpyFromAdmin(reply, False)
    pointName = msg.text

    # TODO ask about work hours

    botLogger.debug('saving point:' + str((msg.chat.id, pointName, pointCity)))
    dbFunc.addNewPoint(msg.chat.id, pointCity, pointName, '')
    reply = bot.send_message(msg.chat.id, 'data saved')
    yield reply, True


def regPoint(msg: telebot.types.Message, gen):
    botLogger.debug('next reg iteration')
    reply, stopReg = gen.send(msg)
    if not stopReg:
        bot.register_next_step_handler(reply, regPoint, gen)


@bot.message_handler(commands=['start'], func=lambda message: message.chat.type == 'supergroup')
def welcomePoint(msg: telebot.types.Message):
    # TODO validate group
    botLogger.debug('welcome point')
    botLogger.debug('got msg from:' + bot.get_chat_member(msg.chat.id, msg.from_user.id).status)
    regGenerator = regPointGen(msg)
    reply, stopReg = next(regGenerator)
    if not stopReg:
        bot.register_next_step_handler(reply, regPoint, regGenerator)

# -reg client functions
def regClientGen(msg: telebot.types.Message):
    reply = bot.send_message(msg.chat.id, 'ask about his name')
    msg: telebot.types.Message = yield reply, False
    clientName = msg.text

    cityKeyboard = telebot.types.ReplyKeyboardMarkup()  # prepare keybaard
    cityList = dbFunc.getCityList()
    for city in cityList:
        cityKeyboard.add(city)

    reply = bot.send_message(msg.chat.id, 'ask about city, say about /rename', reply_markup=cityKeyboard)
    msg = yield reply, False
    clientCity = msg.text
    while clientCity not in cityList:  # wait for correct city
        reply = bot.send_message(msg.chat.id, 'incorrect city')
        msg = yield reply, False
        clientCity = msg.text

    pointKeyboard = telebot.types.ReplyKeyboardMarkup()  # prepare keyboard
    pointList = dbFunc.getPointsByCity(clientCity)
    for point in pointList:
        pointKeyboard.add(point[2])

    reply = bot.send_message(msg.chat.id, 'ask about point, say about /change_city', reply_markup=pointKeyboard)
    msg = yield reply, False
    clientBind = msg.text  # client is binding to point
    while clientBind not in map(lambda el: el[2], pointList):  # wait for correct point
        reply = bot.send_message(msg.chat.id, 'incorrect point')
        msg = yield reply, False
        clientBind = msg.text

    # find point by point name
    clientBindId = next(pTuple for pTuple in pointList if pTuple[2] == clientBind and pTuple[1] == clientCity)[0]

    botLogger.debug('saving client:' + str((msg.chat.id, clientName, clientCity, clientBindId)))
    dbFunc.addNewClient(msg.chat.id, clientName, clientCity, clientBindId)

    reply = bot.send_message(msg.chat.id, 'data saved, say about /change_point', reply_markup=telebot.types.ReplyKeyboardRemove())
    yield reply, True


def regClient(msg: telebot.types.Message, gen):
    botLogger.debug('next reg iteration')
    reply, stopReg = gen.send(msg)
    if not stopReg:
        bot.register_next_step_handler(reply, regClient, gen)


@bot.message_handler(commands=['start'], func=lambda message: message.chat.type == 'private')
def welcomeClient(msg: telebot.types.Message):
    botLogger.debug('welcome user')
    regGenerator = regClientGen(msg)
    reply, stopReg = next(regGenerator)
    if not stopReg:
        bot.register_next_step_handler(reply, regClient, regGenerator)

# -reg consultant
@bot.message_handler(commands=['set_name'], func = lambda msg: dbFunc.getPointById(msg.chat.id) is not None)
def setNameConsultant(msg: telebot.types.Message):
    botLogger.debug('set name for user:' + str(msg.from_user.id) + ' on ' + msg.text)
    dbFunc.addNewConsultant(msg.from_user.id, msg.text)

bot.polling(none_stop=True)
