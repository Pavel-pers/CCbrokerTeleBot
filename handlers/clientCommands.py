from typing import Generator

import telebot
import logging

from locLibs import dbFunc, botTools, simpleClasses
from handlers import threadWorker
from handlers.decorators.stageFileters import regClient as regDecorator
from constants import Replicas, Emoji
from constants.Config import PointType


class Handlers(simpleClasses.Handlers):
    # reg client functions
    def setupClientGen(self, msg: telebot.types.Message, client_name: str = None, client_city: str = None,
                       client_bind: tuple[PointType, int] | None = None) -> \
            Generator[
                tuple[telebot.types.Message, bool],
                telebot.types.Message,
                None
            ]:
        if client_name is None:
            reply = self.bot.send_message(msg.chat.id, Replicas.ASK_NAME_CLIENT)
            msg: telebot.types.Message = yield reply, False
            client_name = msg.text
            self.bot.send_message(msg.chat.id, Replicas.ON_GET_NAME + ', ' + msg.text + ' ' + Emoji.HANDSHAKE)
        if client_city is None:
            cityList = dbFunc.getRegCities()
            cityIndex = yield from botTools.askWithKeyboard(msg.chat.id, Replicas.ASK_CITY_CLIENT, cityList, False)

            client_city = cityList[cityIndex]

        if client_bind is None:
            pointsInCity = dbFunc.getPointsByCity(client_city)
            pointTypesList = []
            if pointsInCity.retail is not None:
                pointTypesList.append(Replicas.RETAIL)
            if pointsInCity.wholesale is not None:
                pointTypesList.append(Replicas.WHOLESALE)
            if len(pointsInCity.service_stations) != 0:
                pointTypesList.append(Replicas.SERVICE_STATION)

            pointTypeIndex = yield from botTools.askWithKeyboard(msg.chat.id, Replicas.ASK_POINT_TYPE_CLIENT,
                                                                 pointTypesList, False)
            clientType = Replicas.POINT_TYPE_DICT[pointTypesList[pointTypeIndex]]
            clientBindId = None
            if clientType is PointType.service_station:
                if len(pointsInCity.service_stations) > 1:
                    service_stations = []
                    for ss in pointsInCity.service_stations:
                        service_stations.append(ss.name)

                    serviceIndex = yield from botTools.askWithKeyboard(msg.chat.id, Replicas.ASK_POINT_PLACE_CLIENT,
                                                                       service_stations, False)
                    clientBindId = pointsInCity.service_stations[serviceIndex].id
                else:
                    clientBindId = pointsInCity.service_stations[0].id
            if clientType is PointType.retail:
                clientBindId = pointsInCity.retail.id
            if clientType is PointType.wholesale:
                clientBindId = pointsInCity.wholesale.id

            client_bind = (clientType, clientBindId)
        else:
            clientType, clientBindId = client_bind

        client = dbFunc.Client(msg.from_user.id, client_name, client_city, clientType, clientBindId)
        self.logger.debug('saving client:' + str((msg.from_user.id, client)))
        dbFunc.addNewClient(client)

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

        replaceProc = self.setupClientGen(msg, client_name=client.name)
        reply, stopReg = next(replaceProc)
        if not stopReg:
            self.bot.register_next_step_handler(reply, self.setupProducer, replaceProc)

    def changeClientName(self, msg: telebot.types.Message):
        client = dbFunc.getClientById(msg.chat.id)
        if client is None:
            self.bot.send_message(msg.chat.id, Replicas.WELCOME_CLIENT)
            return

        renameProc = self.setupClientGen(msg, client_city=client.city, client_bind=client.bind_id)
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
