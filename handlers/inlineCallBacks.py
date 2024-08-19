import threading

import telebot
import logging
import queue

from constants import Inline, Config, UserStages, Replicas
from locLibs import dbFunc
from locLibs import botTools
from locLibs import reminders
from locLibs.simpleClasses import DataForCallBacks, Handlers
from handlers import threadWorker

dataForCb = DataForCallBacks()
threadQ = queue.Queue()


def addCbData(key, data):
    dataForCb.add(key, data, Config.INLINE_DELAY)


class CbHandlers(Handlers):
    def __init__(self):
        super().__init__()

    def postCancelContinue(self, call: telebot.types.CallbackQuery):
        chatId = call.message.chat.id
        msgId = call.message.id
        cbData = dataForCb.get((chatId, None))
        self.logger.debug('work on post cancel/continue callback: saved data: ' + str(cbData))
        self.bot.clear_step_handler_by_chat_id(chatId)

        if call.data == Inline.POST_CANCEL:
            if cbData is None and dbFunc.getTaskByClientId(call.message.chat.id) is not None:
                self.bot.edit_message_text(Replicas.ERROR_ALREADY_IN_CONVERASTION, chatId, msgId)
            else:
                self.bot.edit_message_text(Replicas.ON_TASK_CANCEL, chatId, msgId)
                self.bot.send_message(chatId, Replicas.ABOUT_CHANGE_DATA_CLIENT + '\n\n' + Replicas.SAY_ABOUT_ASK_QUESTION)
        elif call.data == Inline.POST_CONTINUE:
            if cbData is None:
                self.bot.send_message(chatId, Replicas.ASK_TO_REPEAT_CLIENT)
                self.bot.edit_message_text(call.message.text, chatId, msgId)
            else:  # client starts the conversation
                client, pointName, msg = cbData
                self.bot.set_state(client[0], UserStages.CLIENT_IN_CONVERSATION)
                self.bot.edit_message_text(Replicas.ON_TASK_CONTINUE, chatId, msgId)
                channel, postId = botTools.addNewTask(client, msg)
                topicId = botTools.startFrorward(client[2], client[1], pointName)
                botTools.forwardMessage(topicId, msg)
                dbFunc.addNewTask(client[0], channel, postId, topicId)
                reminders.regReminder(client[3], client[0], client[1])
        else:
            raise 'inline callback data error'

    def rateHandler(self, call: telebot.types.CallbackQuery):
        rate = int(call.data.split(':')[1])
        chatId = call.message.chat.id
        messageId = call.message.id
        cbData = dataForCb.get((chatId, messageId))
        self.bot.edit_message_text(Replicas.THANKS_FOR_RATE, chatId, messageId)

        if cbData is None:
            self.logger.warning('client rate deleted post')
            return

        activeIds, topicId, bonus = cbData
        self.logger.debug('rate_inline_callback info:' + str(cbData))
        botTools.forwardRate(topicId, rate)

        for consultant in activeIds:
            dbFunc.addRateConsultant(consultant, rate, bonus)


handlers = CbHandlers()


def startListen(bot: telebot.TeleBot, botLogger: logging.Logger, ignoreErr=False):
    # post cancel or continue, listener
    handlers.set_bot(bot)
    handlers.set_logger(botLogger)

    workerPool = [threading.Thread(target=threadWorker.worker, args=(threadQ, botLogger, ignoreErr)) for i in range(3)]
    for i in workerPool:
        i.start()

    @bot.callback_query_handler(func=lambda call: call.data in [Inline.POST_CANCEL, Inline.POST_CONTINUE])
    def postCancelContinue(call: telebot.types.CallbackQuery):
        threadQ.put((handlers.postCancelContinue, (call,)))

    @bot.callback_query_handler(func=lambda call: call.data.startswith(Inline.RATE_PREF))
    def rateHandler(call: telebot.types.CallbackQuery):
        threadQ.put((handlers.rateHandler, (call,)))
