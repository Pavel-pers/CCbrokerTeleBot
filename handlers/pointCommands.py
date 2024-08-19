import telebot
from locLibs import dbFunc
from locLibs import botTools
from locLibs import simpleTools
from locLibs import simpleClasses
from constants import UserStages, Config, Replicas
import logging
from re import compile

pendingPermitions = simpleClasses.PendingPermissions()


def startListen(bot: simpleClasses.TeleBotBanF, botLogger: logging.Logger):
    def unknownGroupHandler(msg: telebot.types.Message):
        state = bot.get_state(msg.chat.id)
        if state == UserStages.WARN[2]:
            bot.send_message(msg.chat.id, Replicas.BANNED_TEXT)
            bot.block_user(msg.chat.id)
        elif state in UserStages.WARN:
            bot.send_message(msg.chat.id, Replicas.WARN_PREFIX + str(state - UserStages.WARN[0] + 1))
            bot.set_state(msg.chat.id, state + 1)
        else:
            secret = (msg.chat.id % 90) + 10
            bot.send_message(msg.chat.id, Replicas.SECRET_CODE_PREFIX + str(secret))
            bot.set_state(msg.chat.id, UserStages.WARN[0])

    def regPointGen(msg: telebot.types.Message, pointExists: bool):
        msg: telebot.types.Message
        cityList = dbFunc.getCities()
        cityNames = list(map(lambda x: x[0], cityList))
        pointIndex = yield from botTools.askWithKeyboard(msg.chat.id, Replicas.WELCOME_POINT, cityNames, True)
        pointCity, pointZone = cityList[pointIndex]

        reply = bot.send_message(msg.chat.id, Replicas.ASK_WORK_HOURS_POINT,
                                 reply_markup=telebot.types.ReplyKeyboardRemove())
        msg = yield from botTools.waitRelpyFromAdmin(reply, False)
        while not simpleTools.workH_pattern.match(msg.text):
            reply = bot.send_message(msg.chat.id, Replicas.INCORECT_FORMAT)
            msg = yield from botTools.waitRelpyFromAdmin(reply, False)
        workH = msg.text
        start, finish = workH.split('-')
        start = simpleTools.timezoneConv(start, pointZone)
        finish = simpleTools.timezoneConv(finish, pointZone)
        workH = start + '-' + finish

        reply = bot.send_message(msg.chat.id, Replicas.ASK_NAME_POINT)
        msg = yield from botTools.waitRelpyFromAdmin(reply, False)
        pointName = msg.text

        botLogger.debug('saving point:' + str((msg.chat.id, pointName, pointCity)))

        if pointExists:
            dbFunc.updatePoint(msg.chat.id, pointCity, pointName, workH)
        else:
            dbFunc.addNewPoint(msg.chat.id, pointCity, pointName, workH)
        reply = bot.send_message(msg.chat.id, Replicas.ON_REGISTRATION_POINT)
        yield reply, True

    def regPoint(msg: telebot.types.Message, gen):
        botLogger.debug('next reg iteration')
        reply, stopReg = gen.send(msg)
        if not stopReg:
            bot.register_next_step_handler(reply, regPoint, gen)

    # begin work with point
    #   -reg handler
    @bot.message_handler(commands=['start'],
                         func=lambda msg: msg.chat.type == 'supergroup' and botTools.isFromAdmin(msg))
    def welcomePoint(msg: telebot.types.Message):
        pointExists = botTools.isMsgFromPoint(msg)
        if not pointExists and not pendingPermitions.get((msg.chat.id % 90) + 10):
            unknownGroupHandler(msg)
            return

        botLogger.debug('welcome point')
        botLogger.debug('got msg from:' + bot.get_chat_member(msg.chat.id, msg.from_user.id).status)
        regGenerator = regPointGen(msg, pointExists)
        reply, stopReg = next(regGenerator)
        if not stopReg:
            bot.register_next_step_handler(reply, regPoint, regGenerator)

    bot.message_handler(content_types=Config.ALLOWED_CONTENT,
                        func=lambda msg: msg.chat.type == 'supergroup' and not botTools.isMsgFromPoint(msg))(
        unknownGroupHandler)  # *this handler must process only after previous check

    # ?      after goes handlers without checking if group unknow
    #   -delete handler
    @bot.message_handler(commands=['delete_point'], func=lambda msg: msg.chat.type == 'supergroup')
    def deletePoint(msg: telebot.types.Message):
        if not botTools.isFromAdmin(msg):
            bot.send_message(msg.chat.id, Replicas.ONLY_ADMIN)
        elif not dbFunc.isPointClear(msg.chat.id):
            bot.send_message(msg.chat.id, Replicas.NOT_ALL_ANSWERED)
        else:
            dbFunc.delPoint(msg.chat.id)
            bot.send_message(msg.chat.id, Replicas.ON_DELETE_POINT)
