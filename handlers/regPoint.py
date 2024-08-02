import telebot
from locLibs import dbFunc
from locLibs import botTools
from locLibs import simpleTools
import logging
from re import compile


def startListen(bot: telebot.TeleBot, botLogger: logging.Logger):
    def regPointGen(msg: telebot.types.Message):
        msg: telebot.types.Message
        cityList = dbFunc.getCities()
        cityNames = list(map(lambda x: x[0], cityList))
        pointIndex = yield from botTools.askWithKeyboard(msg.chat.id, 'welcome group, ask about city', cityNames, True)
        pointCity, pointZone = cityList[pointIndex]

        reply = bot.send_message(msg.chat.id,
                                 'ask about work hours, in current city timezone, format\nHH:MM-HH:MM',
                                 reply_markup=telebot.types.ReplyKeyboardRemove())
        msg = yield from botTools.waitRelpyFromAdmin(reply, False)
        while not simpleTools.workH_pattern.match(msg.text):
            reply = bot.send_message(msg.chat.id, 'incorrect format')
            msg = yield from botTools.waitRelpyFromAdmin(reply, False)
        workH = msg.text
        start, finish = workH.split('-')
        start = simpleTools.timezoneConv(start, pointZone)
        finish = simpleTools.timezoneConv(finish, pointZone)
        workH = start + '-' + finish

        reply = bot.send_message(msg.chat.id, 'ask about name say about /rename')
        msg = yield from botTools.waitRelpyFromAdmin(reply, False)
        pointName = msg.text

        botLogger.debug('saving point:' + str((msg.chat.id, pointName, pointCity)))
        dbFunc.addNewPoint(msg.chat.id, pointCity, pointName, workH)
        reply = bot.send_message(msg.chat.id, 'data saved')
        yield reply, True

    def regPoint(msg: telebot.types.Message, gen):
        botLogger.debug('next reg iteration')
        reply, stopReg = gen.send(msg)
        if not stopReg:
            bot.register_next_step_handler(reply, regPoint, gen)

    # begin work with point
    @bot.message_handler(commands=['start'],
                         func=lambda msg: msg.chat.type == 'supergroup' and botTools.isFromAdmin(msg))
    def welcomePoint(msg: telebot.types.Message):
        # TODO validate group
        botLogger.debug('welcome point')
        botLogger.debug('got msg from:' + bot.get_chat_member(msg.chat.id, msg.from_user.id).status)
        regGenerator = regPointGen(msg)
        reply, stopReg = next(regGenerator)
        if not stopReg:
            bot.register_next_step_handler(reply, regPoint, regGenerator)
