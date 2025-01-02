import telebot
import logging

from handlers import threadWorker
from locLibs import dbFunc
from locLibs import botTools
from constants import Replicas, Config


def startListen(bot: telebot.TeleBot, botLogger: logging.Logger, ignoreErrs: bool = False):
    pool = threadWorker.PoolHandlers(1, botLogger, ignoreErrs, lambda *args: 0, handler_name="ConsultantHandler")

    @bot.chat_member_handler(func=lambda message: botTools.is_new_user_event(message))
    @pool.handlerDecorator
    def welcome_consultant(event: telebot.types.ChatMemberUpdated):
        new_user_id = event.new_chat_member.user.id
        if not event.invite_link:
            bot.send_message(event.chat.id, Replicas.JOIN_NOT_FROM_LINK)
            bot.kick_chat_member(event.chat.id, new_user_id)
            bot.unban_chat_member(event.chat.id, new_user_id)
            return

        invite_link = event.invite_link.invite_link
        invite_name = event.invite_link.name
        if not invite_name.startswith(Config.INVITE_LINK_PREFIX):
            bot.send_message(event.chat.id, Replicas.JOIN_NOT_FROM_MY_LINK)
            bot.kick_chat_member(event.chat.id, new_user_id)
            bot.unban_chat_member(event.chat.id, new_user_id)
            return

        link_info = invite_name[len(Config.INVITE_LINK_PREFIX):]
        bot.revoke_chat_invite_link(event.chat.id, invite_link)
        dbFunc.addNewConsultant(new_user_id, link_info, event.chat.id)

    @bot.message_handler(commands=['invite', 'add_consultant'])
    @pool.handlerDecorator
    def add_consultant(msg: telebot.types.Message):
        if not botTools.isFromAdmin(msg):
            bot.send_message(msg.chat.id, Replicas.ONLY_ADMIN)
            return

        if ' ' not in msg.text:
            bot.send_message(msg.chat.id, Replicas.NOT_FULL_INVITE_COMMAND)
        else:
            name = msg.text[msg.text.find(' ') + 1:]

            botLogger.debug("send link for " + str(msg.chat.type))
            invite_link = bot.create_chat_invite_link(msg.chat.id,
                                                      Config.INVITE_LINK_PREFIX + name).invite_link  # TODO test on same names
            channel_id = bot.get_chat(msg.chat.id).linked_chat_id
            channel_link = bot.get_chat(channel_id).invite_link
            print(channel_link)
            bot.send_message(msg.chat.id, Replicas.GENERATE_LINK.format(channel_link, invite_link), parse_mode='HTML')

    @bot.message_handler(commands=['set_name'], func=botTools.isMsgFromPoint)
    @pool.handlerDecorator
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
