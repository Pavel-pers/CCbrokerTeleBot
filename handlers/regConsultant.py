import telebot
from locLibs import dbFunc
from locLibs.botTools import *
import logging


def startListen(bot: telebot.TeleBot, botLogger: logging.Logger):
    @bot.message_handler(commands=['set_name', 'rename'], func=lambda msg: dbFunc.getPointById(msg.chat.id) is not None)
    def setNameConsultant(msg: telebot.types.Message):
        name = msg.text
        if ' ' not in name:
            bot.send_message(msg.chat.id, 'incorect format')
            return
        name = name[name.find(' ') + 1:]
        botLogger.debug('set name for user:' + str(msg.from_user.id) + ' on ' + name)
        bot.send_message(msg.chat.id, 'data saved')
        dbFunc.addNewConsultant(msg.from_user.id, name, msg.chat.id)
