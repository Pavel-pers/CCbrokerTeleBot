import telebot
from locLibs import dbFunc
from locLibs import botTools
from locLibs.simpleClasses import DataForInlineCB
import logging
from constants import Inline, Config, UserStages

dataForCb = DataForInlineCB()


def addCbData(key, data):
    dataForCb.add(key, data, Config.INLINE_DELAY)


def startListen(bot: telebot.TeleBot, botLogger: logging.Logger):
    # post cancel or continue, listener
    @bot.callback_query_handler(func=lambda call: call.data in [Inline.POST_CANCEL, Inline.POST_CONTINUE])
    def postCancelContinue(call: telebot.types.CallbackQuery):
        chatId = call.message.chat.id
        msgId = call.message.id
        cbData = dataForCb.get((chatId, None))
        botLogger.debug('work on post cancel/continue callback: saved data: ' + str(cbData))
        bot.clear_step_handler_by_chat_id(chatId)
        if call.data == Inline.POST_CANCEL:
            bot.edit_message_text('post has canceled', chatId, msgId)
            bot.send_message(chatId, 'enter /rename to rename, enter /set_point to replace')
        else:
            if cbData is None:
                bot.send_message(chatId, 'can you repeat your request?')
                bot.edit_message_text(call.message.text, chatId, msgId)
            else:  # client starts the conversation
                client, msg = cbData
                bot.set_state(client[0], UserStages.CLIENT_IN_CONVERSATION)
                bot.edit_message_text('message has sent', chatId, msgId)
                botTools.addNewTask(client, msg)

    @bot.callback_query_handler(func=lambda call: call.data == Inline.POST_QUIT)
    def postQuit(call: telebot.types.CallbackQuery):
        chatId = call.message.chat.id
        bot.edit_message_text(call.message.text, chatId, call.message.id)
        botTools.endTask(chatId)
