import telebot
from locLibs import dbFunc
from locLibs.botTools import *
import logging


def startListen(bot: telebot.TeleBot, botLogger: logging.Logger):
    def regPointGen(msg: telebot.types.Message):
        cityKeyboard = telebot.types.ReplyKeyboardMarkup()
        cityList = dbFunc.getCityList()

        for city in cityList:
            cityKeyboard.add(city)

        reply = bot.send_message(msg.chat.id, 'welcome group, ask about city', reply_markup=cityKeyboard)
        msg: telebot.types.Message = yield from waitRelpyFromAdmin(reply, False)
        pointCity = msg.text

        while pointCity not in cityList:
            reply = bot.send_message(msg.chat.id, 'incorrect city', reply_markup=cityKeyboard)
            msg = yield from waitRelpyFromAdmin(reply, False)
            pointCity = msg.text

        reply = bot.send_message(msg.chat.id, 'ask about name say about /rename',
                                 reply_markup=telebot.types.ReplyKeyboardRemove())
        msg = yield from waitRelpyFromAdmin(reply, False)
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

    # begin work with point
    @bot.message_handler(commands=['start'], func=lambda message: message.chat.type == 'supergroup')
    def welcomePoint(msg: telebot.types.Message):
        # TODO validate group
        botLogger.debug('welcome point')
        botLogger.debug('got msg from:' + bot.get_chat_member(msg.chat.id, msg.from_user.id).status)
        regGenerator = regPointGen(msg)
        reply, stopReg = next(regGenerator)
        if not stopReg:
            bot.register_next_step_handler(reply, regPoint, regGenerator)
