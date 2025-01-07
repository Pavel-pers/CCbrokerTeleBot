from typing import Generator

import telebot
import logging

from locLibs import dbFunc, botTools, simpleTools, simpleClasses
from handlers import threadWorker
from constants import UserStages, Config, Replicas

pendingPermitions = simpleClasses.PendingPermissions()


class Handlers(simpleClasses.Handlers):
    def unknownGroupHandler(self, msg: telebot.types.Message):
        state = self.bot.get_state(msg.chat.id)
        if state == UserStages.WARN[2]:
            self.bot.send_message(msg.chat.id, Replicas.BANNED_TEXT)
            self.bot.block_user(msg.chat.id)
        elif state in UserStages.WARN:
            self.bot.send_message(msg.chat.id, Replicas.WARN_PREFIX + str(state - UserStages.WARN[0] + 1))
            self.bot.set_state(msg.chat.id, state + 1)
        else:
            secret = (msg.chat.id % 90) + 10
            self.bot.send_message(msg.chat.id, Replicas.SECRET_CODE_PREFIX + str(secret))
            self.bot.set_state(msg.chat.id, UserStages.WARN[0])

    def regPointGen(self, msg: telebot.types.Message, pointExists: bool) -> Generator[
        tuple[telebot.types.Message, bool],
        telebot.types.Message,
        None
    ]:
        msg: telebot.types.Message
        cityList = dbFunc.getCities()
        cityNames = list(map(lambda x: x[0], cityList))
        pointIndex = yield from botTools.askWithKeyboard(msg.chat.id, Replicas.WELCOME_POINT, cityNames, True)
        pointCity, pointZone = cityList[pointIndex]

        reply = self.bot.send_message(msg.chat.id, Replicas.ASK_WORK_HOURS_POINT,
                                      reply_markup=telebot.types.ReplyKeyboardRemove())
        msg = yield from botTools.waitRelpyFromAdmin(reply, False)
        while not simpleTools.workH_pattern.match(msg.text):
            reply = self.bot.send_message(msg.chat.id, Replicas.INCORECT_FORMAT)
            msg = yield from botTools.waitRelpyFromAdmin(reply, False)
        workH_local = msg.text
        start, finish = workH_local.split('-')
        start = simpleTools.timezoneConv(start, pointZone)
        finish = simpleTools.timezoneConv(finish, pointZone)
        workH_global = start + '-' + finish

        pointsInCity = dbFunc.getPointsByCity(pointCity)
        avalibaleTypes = [Replicas.SERVICE_STATION]
        if pointsInCity.retail is None or pointsInCity.retail == msg.chat.id:
            avalibaleTypes.append(Replicas.RETAIL)
        if pointsInCity.wholesale is None or pointsInCity.wholesale == msg.chat.id:
            avalibaleTypes.append(Replicas.WHOLESALE)

        type_index = yield from botTools.askWithKeyboard(msg.chat.id, Replicas.ASK_POINT_TYPE, avalibaleTypes, True)
        pointType = Replicas.POINT_TYPE_DICT[avalibaleTypes[type_index]]
        reply = self.bot.send_message(msg.chat.id, Replicas.ASK_NAME_POINT, reply_markup=telebot.types.ReplyKeyboardRemove())
        msg = yield from botTools.waitRelpyFromAdmin(reply, False)
        pointName = msg.text

        self.logger.debug('saving point:' + str((msg.chat.id, pointType, pointName, pointCity)))

        if pointExists:
            dbFunc.updatePoint(msg.chat.id, pointCity, pointName, workH_global, pointType)
        else:
            dbFunc.addNewPoint(msg.chat.id, pointCity, pointName, workH_global, pointType)
        botTools.forawrdPointCreate(pointCity, pointType, pointName, workH_local, msg.from_user.id, msg.from_user.username)
        reply = self.bot.send_message(msg.chat.id, Replicas.ON_REGISTRATION_POINT, parse_mode="HTML")
        yield reply, True

    def regPointProducer(self, msg, generator):
        self.putTask(self.regPoint, (msg, generator))

    def regPoint(self, msg: telebot.types.Message, gen):
        self.logger.debug('next reg iteration')
        reply, stopReg = gen.send(msg)
        if not stopReg:
            self.bot.register_next_step_handler(reply, self.regPointProducer, gen)

    # begin work with point
    #   -reg handler
    def welcomePoint(self, msg: telebot.types.Message):
        pointExists = botTools.isMsgFromPoint(msg)
        if not pointExists and not pendingPermitions.get((msg.chat.id % 90) + 10):
            self.unknownGroupHandler(msg)
            return

        self.logger.debug('welcome point')
        self.logger.debug('got msg from:' + self.bot.get_chat_member(msg.chat.id, msg.from_user.id).status)
        regGenerator = self.regPointGen(msg, pointExists)
        reply, stopReg = next(regGenerator)
        if not stopReg:
            self.bot.register_next_step_handler(reply, self.regPointProducer, regGenerator)

    # ?      after goes handlers without checking if group unknow
    #   -delete point handler
    def deletePoint(self, msg: telebot.types.Message):
        if not botTools.isFromAdmin(msg):
            self.bot.send_message(msg.chat.id, Replicas.ONLY_ADMIN)
        elif not dbFunc.isPointClear(msg.chat.id):
            self.bot.send_message(msg.chat.id, Replicas.NOT_ALL_ANSWERED)
        else:
            dbFunc.delPoint(msg.chat.id)
            self.bot.send_message(msg.chat.id, Replicas.ON_DELETE_POINT)


handlers = Handlers()


def startListen(bot: simpleClasses.TeleBotBanF, botLogger: logging.Logger, ignoreErrs: bool = False):
    pool = threadWorker.PoolHandlers(1, botLogger, ignoreErrs, lambda *args: 0, "PointChatHandler")
    handlers.set_bot(bot)
    handlers.set_logger(botLogger)
    handlers.set_work_queue_interactor(pool.addTask)

    bot.message_handler(commands=['start'],
                        func=lambda msg: msg.chat.type == 'supergroup' and botTools.isFromAdmin(msg))(
        pool.handlerDecorator(
            handlers.welcomePoint
        )
    )
    bot.message_handler(content_types=Config.ALLOWED_CONTENT,
                        func=lambda msg: msg.chat.type == 'supergroup' and not botTools.isMsgFromPoint(msg))(
        pool.handlerDecorator(
            handlers.unknownGroupHandler
        )
    )  # ? must go after previous handler

    bot.message_handler(commands=['delete_point'], func=lambda msg: msg.chat.type == 'supergroup')(
        pool.handlerDecorator(
            handlers.deletePoint
        )
    )
