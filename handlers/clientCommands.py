from typing import Generator

import telebot
import logging

from locLibs import dbFunc, botTools, simpleClasses
from handlers import threadWorker
from handlers.decorators.stageFileters import regClient as regDecorator
from constants import Replicas, Emoji


class Handlers(simpleClasses.Handlers):
    # reg client functions
    def setupClientGen(self, msg: telebot.types.Message, client=(None, None, None)) -> Generator[
        tuple[telebot.types.Message, bool],
        telebot.types.Message,
        None
    ]:
        if client[0] is None:
            reply = self.bot.send_message(msg.chat.id, Replicas.ASK_NAME_CLIENT)
            msg: telebot.types.Message = yield reply, False
            client = (msg.text, client[1], client[2])
            self.bot.send_message(msg.chat.id, Replicas.ON_GET_NAME + ', ' + msg.text + ' ' + Emoji.HANDSHAKE)
        if client[1] is None:
            cityList = dbFunc.getRegCities()
            cityIndex = yield from botTools.askWithKeyboard(msg.chat.id, Replicas.ASK_CITY_CLIENT, cityList, False)

            clientCity = cityList[cityIndex]
            client = (client[0], clientCity, client[2])
        else:
            clientCity = client[1]

        if client[2] is None:
            pointList = dbFunc.getPointsByCity(clientCity)
            pointIndex = yield from botTools.askWithKeyboard(msg.chat.id, Replicas.ASK_POINT_CLIENT,
                                                             list(map(lambda x: x[2], pointList)), False)
            clientBindId = pointList[pointIndex][0]
            client = (client[0], client[1], clientBindId)

        self.logger.debug('saving client:' + str((msg.from_user.id, client)))
        dbFunc.addNewClient(msg.from_user.id, *client)

        reply = self.bot.send_message(msg.chat.id, Replicas.ON_REGISTRATION_CLIENT,
                                      reply_markup=telebot.types.ReplyKeyboardRemove())
        yield reply, True

    def setupProducer(self, msg, generator):
        self.putTask(self.setupClientIterate, (msg, generator))

    def setupClientIterate(self, msg: telebot.types.Message, gen):
        self.logger.debug('next reg iteration')
        reply, stopReg = gen.send(msg)
        if not stopReg:
            self.bot.register_next_step_handler(reply, self.setupProducer, gen)

    def setupClient(self, msg: telebot.types.Message):
        self.logger.debug('welcome user')
        regProc = self.setupClientGen(msg)
        reply, stopReg = next(regProc)
        if not stopReg:
            self.bot.register_next_step_handler(reply, self.setupProducer, regProc)

    # change functions
    def changeClientPoint(self, msg: telebot.types.Message):
        client = dbFunc.getClientById(msg.chat.id)
        if client is None:
            self.bot.send_message(msg.chat.id, Replicas.WELCOME_CLIENT)
            return

        replaceProc = self.setupClientGen(msg, (client[1], None, None))
        reply, stopReg = next(replaceProc)
        if not stopReg:
            self.bot.register_next_step_handler(reply, self.setupProducer, replaceProc)

    def changeClientName(self, msg: telebot.types.Message):
        client = dbFunc.getClientById(msg.chat.id)
        if client is None:
            self.bot.send_message(msg.chat.id, Replicas.WELCOME_CLIENT)
            return

        renameProc = self.setupClientGen(msg, (None, client[2], client[3]))
        reply, stopReg = next(renameProc)
        if not stopReg:
            self.bot.register_next_step_handler(reply, self.setupProducer, renameProc)

    # welcome client function
    def welcome(self, msg: telebot.types.Message):
        self.bot.send_message(msg.chat.id, Replicas.WELCOME_CLIENT)


handlers = Handlers()


def startListen(bot: telebot.TeleBot, botLogger: logging.Logger, ignoreErrs: bool = False):
    pool = threadWorker.PoolHandlers(2, botLogger, ignoreErrs, lambda msg, *args: msg.chat.id % 2,
                                     handler_name="ClientHandler")
    handlers.set_bot(bot)
    handlers.set_logger(botLogger)
    handlers.set_work_queue_interactor(pool.addTask)

    # begin work with client
    bot.message_handler(commands=['setup'],
                        func=lambda msg: msg.chat.type == 'private' and bot.get_state(msg.chat) is None)(
        regDecorator(bot)(
            pool.handlerDecorator(
                handlers.setupClient
            )
        )
    )

    bot.message_handler(commands=['start'],
                        func=lambda msg: msg.chat.type == 'private' and bot.get_state(msg.chat) is None)(
        regDecorator(bot)(
            pool.handlerDecorator(
                handlers.welcome
            )
        )
    )
    # change functional
    #   -change point
    bot.message_handler(commands=['change_point'],
                        func=lambda message: message.chat.type == 'private')(
        regDecorator(bot)(
            pool.handlerDecorator(
                handlers.changeClientPoint
            )
        )
    )

    #   -change name
    bot.message_handler(commands=['rename'], func=lambda message: message.chat.type == 'private')(
        regDecorator(bot)(
            pool.handlerDecorator(
                handlers.changeClientName
            )
        )
    )
