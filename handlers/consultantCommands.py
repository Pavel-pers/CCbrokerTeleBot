import telebot
from locLibs import dbFunc
from locLibs.botTools import *
import logging
from constants import Replicas


def startListen(bot: telebot.TeleBot, botLogger: logging.Logger):
    @bot.message_handler(commands=['set_name', 'rename'], func=lambda msg: dbFunc.getPointById(msg.chat.id) is not None)
    def setNameConsultant(msg: telebot.types.Message):
        replyId = None
        if msg.reply_to_message is not None:
            replyId = msg.reply_to_message.id

        name = msg.text
        if ' ' not in name:
            bot.send_message(msg.chat.id, Replicas.INCORECT_FORMAT)
            return
        name = name[name.find(' ') + 1:]
        botLogger.debug('set name for user:' + str(msg.from_user.id) + ' on ' + name)

        bot.send_message(msg.chat.id, Replicas.ON_REGISTRATION_CONSULTANT, reply_to_message_id=replyId)
        dbFunc.addNewConsultant(msg.from_user.id, name, msg.chat.id)
