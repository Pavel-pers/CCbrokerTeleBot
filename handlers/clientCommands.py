import telebot
from locLibs import dbFunc
from locLibs import botTools
import logging
from handlers.decorators.stageFileters import regClient as regDecorator
from constants import Config


def startListen(bot: telebot.TeleBot, botLogger: logging.Logger):
    # reg client functions
    def regClientGen(msg: telebot.types.Message, client=(None, None, None)):
        if client[0] is None:
            reply = bot.send_message(msg.chat.id, 'ask about his name')
            msg: telebot.types.Message = yield reply, False
            client = (msg.text, client[1], client[2])

        if client[1] is None:
            cityList = dbFunc.getRegCities()
            cityIndex = yield from botTools.askWithKeyboard(msg.chat.id, 'ask about city', cityList, False)
            clientCity = cityList[cityIndex]
            client = (client[0], clientCity, client[2])
        else:
            clientCity = client[1]

        if client[2] is None:
            pointList = dbFunc.getPointsByCity(clientCity)
            pointIndex = yield from botTools.askWithKeyboard(msg.chat.id, 'ask about point, say about /change_point',
                                                             list(map(lambda x: x[2], pointList)), False)
            clientBindId = pointList[pointIndex][0]
            client = (client[0], client[1], clientBindId)

        botLogger.debug('saving client:' + str((msg.from_user.id, client)))
        dbFunc.addNewClient(msg.from_user.id, *client)

        reply = bot.send_message(msg.chat.id, 'data saved, say about /change_point',
                                 reply_markup=telebot.types.ReplyKeyboardRemove())
        yield reply, True

    def regClient(msg: telebot.types.Message, gen):
        botLogger.debug('next reg iteration')
        reply, stopReg = gen.send(msg)
        if not stopReg:
            bot.register_next_step_handler(reply, regClient, gen)

    # begin work with client
    @bot.message_handler(commands=['start'],
                         func=lambda msg: msg.chat.type == 'private' and bot.get_state(msg.chat) is None)
    @regDecorator(bot)
    def welcomeClient(msg: telebot.types.Message):
        botLogger.debug('welcome user')
        regProc = regClientGen(msg)
        reply, stopReg = next(regProc)
        if not stopReg:
            bot.register_next_step_handler(reply, regClient, regProc)

    # change functional
    #   -change point
    @bot.message_handler(commands=['change_point'],
                         func=lambda message: message.chat.type == 'private')
    @regDecorator(bot)
    def changeClientPoint(msg: telebot.types.Message):
        client = dbFunc.getClientById(msg.chat.id)
        if client is None:
            bot.send_message(msg.chat.id, 'please enter /start for register')
            return

        replaceProc = regClientGen(msg, (client[1], None, None))
        reply, stopReg = next(replaceProc)
        if not stopReg:
            bot.register_next_step_handler(reply, regClient, replaceProc)

    #   -change name
    @bot.message_handler(commands=['set_name', 'rename'], func=lambda message: message.chat.type == 'private')
    @regDecorator(bot)
    def changeClientName(msg: telebot.types.Message):
        client = dbFunc.getClientById(msg.chat.id)
        if client is None:
            bot.send_message(msg.chat.id, 'please enter /start for register')
            return

        renameProc = regClientGen(msg, (None, client[2], client[3]))
        reply, stopReg = next(renameProc)
        if not stopReg:
            bot.register_next_step_handler(reply, regClient, renameProc)
