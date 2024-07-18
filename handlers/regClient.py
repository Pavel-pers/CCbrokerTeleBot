import telebot
from locLibs import dbFunc
from locLibs.botTools import *
import logging
from handlers.decorators.stageFileters import regClient as regDecorator


def startListen(bot: telebot.TeleBot, botLogger: logging.Logger):
    # reg client functions
    def regClientGen(msg: telebot.types.Message, client=(None, None, None)):
        if client[0] is None:
            reply = bot.send_message(msg.chat.id, 'ask about his name')
            msg: telebot.types.Message = yield reply, False
            client = (msg.text, client[1], client[2])

        if client[1] is None:
            cityKeyboard = telebot.types.ReplyKeyboardMarkup()  # prepare keybaard
            cityList = dbFunc.getRegCityList()
            for city in cityList:
                cityKeyboard.add(city)

            reply = bot.send_message(msg.chat.id, 'ask about city, say about /rename', reply_markup=cityKeyboard)
            msg = yield reply, False
            while msg.text not in cityList:  # wait for correct city
                reply = bot.send_message(msg.chat.id, 'incorrect city', reply_markup=cityKeyboard)
                msg = yield reply, False

            client = (client[0], msg.text, client[2])
        clientCity = client[1]

        if client[2] is None:
            pointKeyboard = telebot.types.ReplyKeyboardMarkup()  # prepare keyboard
            pointList = dbFunc.getPointsByCity(clientCity)
            for point in pointList:
                pointKeyboard.add(point[2])

            reply = bot.send_message(msg.chat.id, 'ask about point, say about /change_point',
                                     reply_markup=pointKeyboard)
            msg = yield reply, False
            while msg.text not in map(lambda el: el[2], pointList):  # wait for correct point
                reply = bot.send_message(msg.chat.id, 'incorrect point', reply_markup=pointKeyboard)
                msg = yield reply, False

            # find point by point name
            clientBindId = next(pTuple for pTuple in pointList if pTuple[2] == msg.text and pTuple[1] == clientCity)[0]
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
