import telebot
from locLibs import dbFunc
from locLibs import botTools
from locLibs import simpleTools
from locLibs import simpleClasses
from constants import UserStages, Config
import logging
from re import compile

pendingPermitions = simpleClasses.PendingPermissions()


def startListen(bot: simpleClasses.TeleBotBanF, botLogger: logging.Logger):
    def unknownGroupHandler(msg: telebot.types.Message):
        state = bot.get_state(msg.chat.id)
        if state == UserStages.WARN[2]:
            bot.send_message(msg.chat.id, 'banned!')
            bot.block_user(msg.chat.id)
        elif state in UserStages.WARN:
            bot.send_message(msg.chat.id, 'warning N:' + str(state - UserStages.WARN[0] + 1))
            bot.set_state(msg.chat.id, state + 1)
        else:
            secret = (msg.chat.id % 90) + 10
            bot.send_message(msg.chat.id, 'your secret code is ' + str(secret))
            bot.set_state(msg.chat.id, UserStages.WARN[0])

    def regPointGen(msg: telebot.types.Message, pointExists: bool):
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

        if pointExists:
            dbFunc.updatePoint(msg.chat.id, pointCity, pointName, workH)
        else:
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
        pointExists = botTools.isMsgFromPoint(msg)
        if not pointExists and not pendingPermitions.get(msg.chat.id):
            unknownGroupHandler(msg)

        botLogger.debug('welcome point')
        botLogger.debug('got msg from:' + bot.get_chat_member(msg.chat.id, msg.from_user.id).status)
        regGenerator = regPointGen(msg, pointExists)
        reply, stopReg = next(regGenerator)
        if not stopReg:
            bot.register_next_step_handler(reply, regPoint, regGenerator)

    bot.message_handler(content_types=Config.ALLOWED_CONTENT, func=lambda msg: not botTools.isMsgFromPoint(msg))(
        unknownGroupHandler)
