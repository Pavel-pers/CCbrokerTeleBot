import dataclasses

import telebot
import logging
import queue

from constants import Inline, Config, UserStages, Replicas, Emoji
from locLibs import dbFunc, botTools, reminders
from locLibs.simpleClasses import DataForCallBacks, Handlers, MsgContent
from handlers import threadWorker

dataForCb = DataForCallBacks()
threadQ = queue.Queue()


def addCbData(key, data):
    dataForCb.add(key, data, Config.INLINE_DELAY)


@dataclasses.dataclass
class CbDataCC:
    client: dbFunc.Client
    pointName: str
    msgContent: MsgContent | telebot.types.Message


@dataclasses.dataclass
class CbDataRate:
    activeIds: list[int]
    groupId: int
    topicId: int
    isBonus: bool


class CbHandlers(Handlers):
    def __init__(self):
        super().__init__()

    def postCancelContinue(self, call: telebot.types.CallbackQuery):
        chatId = call.message.chat.id
        msgId = call.message.id
        cbData: CbDataCC | None = dataForCb.get((chatId, None))
        self.logger.debug('cancel/continue callback: saved data: ' + str(cbData))
        self.bot.clear_step_handler_by_chat_id(chatId)

        if call.data == Inline.POST_CANCEL:
            if cbData is None and dbFunc.getTaskByClientId(call.message.chat.id) is not None:
                self.bot.edit_message_text(Replicas.ERROR_ALREADY_IN_CONVERASTION, chatId, msgId)
            else:
                self.bot.edit_message_text(Replicas.ON_TASK_CANCEL, chatId, msgId)
                self.bot.send_message(chatId,
                                      Replicas.ABOUT_CHANGE_DATA_CLIENT + '\n\n' + Replicas.SAY_ABOUT_ASK_QUESTION)
        elif call.data == Inline.POST_CONTINUE:
            if cbData is None:
                self.bot.send_message(chatId, Replicas.ASK_TO_REPEAT_CLIENT)
                self.bot.edit_message_text(call.message.text, chatId, msgId)
            else:  # client starts the conversation
                client, pointName, msg = cbData.client, cbData.pointName, cbData.msgContent
                self.bot.set_state(client.id, UserStages.CLIENT_IN_CONVERSATION)
                self.bot.edit_message_text(Replicas.ON_TASK_CONTINUE, chatId, msgId)

                channel, postId = botTools.addNewTask(client, msg)
                topicId = botTools.startFrorward(client.city, client.name, pointName)
                botTools.forwardMessage(topicId, msg)
                dbFunc.addNewTask(client.id, channel, postId, topicId)
                reminders.regReminder(client.bind_id, client.id, client.name)
        else:
            raise 'inline callback data error'

    def rateHandler(self, call: telebot.types.CallbackQuery):
        rate = int(call.data.split(':')[1])
        chatId = call.message.chat.id
        messageId = call.message.id
        cbData: CbDataRate = dataForCb.get((chatId, messageId))
        self.bot.edit_message_text(Replicas.THANKS_FOR_RATE, chatId, messageId)

        if cbData is None:
            self.logger.warning('client rate deleted post')
            return

        self.logger.debug('rate_inline_callback info:' + str(cbData))
        botTools.forwardRate(cbData.topicId, rate)

        for consultant in cbData.activeIds:
            dbFunc.addRateConsultant(consultant, rate, cbData.isBonus)
        dbFunc.addRatePoint(cbData.groupId, rate)

    def watcherStartTalk(self, call: telebot.types.CallbackQuery):
        clientId = int(call.data[len(Inline.WATCHERS_TALK_PREF):])
        topicId = call.message.message_thread_id
        chatId = call.message.chat.id
        msgId = call.message.id
        dbFunc.addNewClosedTask(clientId=clientId, topicId=topicId)
        self.bot.edit_message_text(Replicas.EDIT_ON_REFLECTION, chatId, msgId)
        self.bot.edit_forum_topic(Config.FORUM_CHAT, topicId, icon_custom_emoji_id=Emoji.VIEWING_TASK)


handlers = CbHandlers()


def startListen(bot: telebot.TeleBot, botLogger: logging.Logger, ignoreErr=False):
    # post cancel or continue, listener
    pool = threadWorker.PoolHandlers(3, botLogger, ignoreErr, lambda call, *args: call.message.chat.id % 3,
                                     handler_name="InlinesHandler")
    handlers.set_bot(bot)
    handlers.set_logger(botLogger)

    bot.callback_query_handler(func=lambda call: call.data in [Inline.POST_CANCEL, Inline.POST_CONTINUE])(
        pool.handlerDecorator(
            handlers.postCancelContinue
        )
    )
    bot.callback_query_handler(func=lambda call: call.data.startswith(Inline.RATE_PREF))(
        pool.handlerDecorator(
            handlers.rateHandler
        )
    )
    bot.callback_query_handler(func=lambda call: call.data.startswith(Inline.WATCHERS_TALK_PREF))(
        pool.handlerDecorator(
            handlers.watcherStartTalk
        )
    )
