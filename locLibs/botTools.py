import functools
from typing import Generator, Callable
from datetime import datetime
import telebot
import time

from locLibs import dbFunc
from locLibs import simpleClasses
from handlers.inlineCallBacks import addCbData
from constants import Emoji, Inline, Config, UserStages, Replicas

bot: simpleClasses.TeleBotBanF


def backupStages():  # add stage to users in conversation
    dbFunc.iterateTable([lambda row: bot.set_state(row[0], UserStages.CLIENT_IN_CONVERSATION)], 'Tasks').wait()


def blockUser(userId):
    bot.block_user(userId)
    dbFunc.addBlockUser(userId)


def is_member(chat_member: telebot.types.ChatMember):
    return chat_member.status == 'member' or chat_member.status == 'creator' or chat_member.status == 'administrator'


def is_new_user_event(event: telebot.types.ChatMemberUpdated):
    return not is_member(event.old_chat_member) and is_member(event.new_chat_member)


def isMsgFromPoint(msg: telebot.types.Message) -> bool:
    pointSet = dbFunc.getPointsIdsSet()
    return msg.chat.type == 'supergroup' and msg.chat.id in pointSet


def linkToTopic(threadId: int):
    return "https://t.me/" + str(Config.FORUM_CHAT)[4:] + "/" + str(threadId)


def redirectMsg(msg: telebot.types.Message, header, **kwargs) -> list[
    Callable[[int, int | None], telebot.types.Message]
]:
    """
    callback generator
    :param parse_mode: parse mode in send_message param
    :param msg: message to redirect
    :param header: prefix text which will be written to redirect message
    :return: tuple of sending functions, which takes params: send_to, reply_to
    """

    text = msg.text or msg.caption or ''
    text = header + '\n' + text

    if msg.content_type == 'text':
        return [lambda ch, repl: bot.send_message(ch, text, reply_to_message_id=repl, **kwargs), ]
    if msg.content_type == 'photo':
        return [lambda ch, repl:
                bot.send_photo(ch, msg.photo[0].file_id, caption=text, reply_to_message_id=repl, **kwargs), ]
    if msg.content_type == 'document':
        return [lambda ch, repl:
                bot.send_document(ch, msg.document.file_id, caption=text, reply_to_message_id=repl, **kwargs), ]
    if msg.content_type == 'audio':
        return [lambda ch, repl:
                bot.send_audio(ch, msg.audio.file_id, caption=text, reply_to_message_id=repl, **kwargs), ]
    if msg.content_type == 'video':
        return [lambda ch, repl:
                bot.send_video(ch, msg.video.file_id, caption=text, reply_to_message_id=repl, **kwargs), ]
    if msg.content_type == 'voice':
        return [lambda ch, repl:
                bot.send_voice(ch, msg.voice.file_id, caption=text, reply_to_message_id=repl, **kwargs), ]
    if msg.content_type == 'video_note':
        return [lambda ch, repl:
                bot.send_message(ch, header + '\n' + Replicas.REDIRECT_VIDEO, reply_to_message_id=repl, **kwargs),
                lambda ch, repl: bot.send_video_note(ch, msg.video_note.file_id, reply_to_message_id=repl)]
    if msg.content_type == 'sticker':
        return [
            lambda ch, repl:
            bot.send_message(ch, header + '\n' + Replicas.REDIRECT_STICKER, reply_to_message_id=repl, **kwargs),
            lambda ch, repl: bot.send_sticker(ch, msg.sticker.file_id, reply_to_message_id=repl)]
    if msg.content_type == 'media_group':
        photos: list[telebot.types.InputMediaPhoto] = list(map(lambda p: p[0], msg.photo))
        photos[0].caption = header + '\n' + (photos[0].caption or '')
        for kw, arg in kwargs.items():
            setattr(photos[0], kw, arg)  # TODO test it
        return (lambda ch, repl: bot.send_media_group(ch, photos, reply_to_message_id=repl, ),)

def isFromAdmin(msg: telebot.types.Message) -> bool:
    return bot.get_chat_member(msg.chat.id, msg.from_user.id).status in ['administrator', 'creator']

def waitRelpyFromAdmin(reply, stopReg) -> Generator[
    tuple[telebot.types.Message, bool],
    telebot.types.Message,
    telebot.types.Message
]:
    msg = yield reply, stopReg
    while not isFromAdmin(msg):
        reply = bot.send_message(msg.chat.id, Replicas.NEED_ADMIN)
        msg = yield reply, False
    return msg

def askWithKeyboard(chatId, header: str, answerList: list, onlyAdmin: bool) -> Generator[
    tuple[telebot.types.Message, bool],
    telebot.types.Message,
    int
]:
    header += '\n' + Replicas.KEYBOARD_INSTRACTION + '\n'

    reply_mrkp = telebot.types.ReplyKeyboardMarkup()
    for i in range(len(answerList)):
        reply_mrkp.add(answerList[i])

    ansIndex = yield from askToChoice(chatId, None, reply_mrkp, header, answerList, onlyAdmin)
    return ansIndex

def askToChoice(chatId, replyId, replyMarkUp, header, answerList, onlyAdmin: bool) -> Generator[
    tuple[telebot.types.Message, bool],
    telebot.types.Message,
    int
]:
    text = header
    for i in range(len(answerList)):
        text += '\n' + str(i + 1) + ': ' + answerList[i]
    reply = bot.send_message(chatId, text, reply_markup=replyMarkUp, reply_to_message_id=replyId)

    answer = ''
    while answer not in answerList and not (answer.isdigit() and 0 < int(answer) <= len(answerList)):
        if answer:
            reply = bot.send_message(chatId, Replicas.INCORECT_FORMAT, reply_markup=replyMarkUp,
                                     reply_to_message_id=replyId)

        if onlyAdmin:
            msg = yield from waitRelpyFromAdmin(reply, False)
        else:
            msg = yield reply, False
        answer = msg.text

    return int(answer) - 1 if answer.isdigit() else answerList.index(answer)

def isPostReply(msg: telebot.types.Message) -> bool:
    return msg.reply_to_message is not None and msg.reply_to_message.from_user.id == 777000 and isMsgFromPoint(msg)

# task funcs
pendingPostMsgs = simpleClasses.PendingMessages()  # messages which waiting telegramm repeat

#   -comments func
def processComments(oldChat, oldReply, newChat, newReply):
    pendingPostMsgs.processCB(oldChat, oldReply, newChat, newReply)

def addComment(chatId, postId, msgFuncs):
    if pendingPostMsgs.isWaiting(chatId, postId):
        for cb in msgFuncs:
            pendingPostMsgs.add(chatId, postId, cb)
    else:
        for cb in msgFuncs:
            cb(chatId, postId)

#   - post message, save in DB
def addNewTask(client, postMsg: telebot.types.Message):
    clientId, clientName, clientCity, clientBind = client
    clientChannel = bot.get_chat(clientBind).linked_chat_id
    header = Replicas.NEW_TASK.format(name=clientName)

    cbList = redirectMsg(postMsg, header)
    post = cbList[0](clientChannel, None)
    replyId = post.message_id if type(post) is telebot.types.Message else post[0].message_id  # check on media group
    pendingPostMsgs.newAwait(clientChannel, replyId)
    for i in cbList[1:]:
        pendingPostMsgs.add(clientChannel, replyId, i)
    return clientChannel, replyId

#   -delete data in DB and ask client
def endTask(clientId):
    inline = telebot.types.InlineKeyboardMarkup()
    for i in range(1, 6):
        inline.add(telebot.types.InlineKeyboardButton(Emoji.RATE[i], callback_data=Inline.RATE_PREF + str(i)))

    reply = bot.send_message(clientId, Replicas.CLOSE_TASK, reply_markup=inline)

    task = dbFunc.getTaskByClientId(clientId)
    groupId = task[1]
    postId = task[2]
    birthTime = task[6]
    bonus = False
    if int(time.time()) - birthTime < Config.BONUS_TIME:
        bot.send_message(groupId, Replicas.QUICK_CLOSE_TASK, reply_to_message_id=postId)
        bonus = True
    else:
        bot.send_message(groupId, Replicas.GENERAL_CLOSE_TASK, reply_to_message_id=postId)

    activeIds = task[4].split(';')[:-1]
    topicId = task[3]
    addCbData((clientId, reply.message_id), (activeIds, groupId, topicId, bonus))
    bot.delete_state(clientId)
    dbFunc.delTask(clientId)

# forwarding func
#   -open task, forum
def maybeTopicNotExistsDecorator(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except telebot.apihelper.ApiTelegramException as e:
            if e.description != 'Bad Request: message thread not found':
                raise e

    return wrapper

def startFrorward(clientCity: str, clientName: str, pointName):
    today_date = datetime.today().strftime('%m/%d %H:%M')
    topic = bot.create_forum_topic(Config.FORUM_CHAT, f'{clientCity} [{today_date}] "{clientName}"',
                                   icon_custom_emoji_id=Emoji.OPEN_TASK)
    bot.send_message(Config.FORUM_CHAT, Replicas.TASK_OPEN_WATCHERS.format(client=clientName, chat=pointName),
                     message_thread_id=topic.message_thread_id)
    return topic.message_thread_id

@maybeTopicNotExistsDecorator
def endFrorward(threadId, clientId):
    inline_to_talk = telebot.types.InlineKeyboardMarkup()
    talk_button = telebot.types.InlineKeyboardButton(Replicas.INLINE_BUTTON_REFLECTION,
                                                     callback_data=Inline.WATCHERS_TALK_PREF + str(clientId))
    inline_to_talk.add(talk_button)
    bot.send_message(Config.FORUM_CHAT, Replicas.TASK_CLOSED_WATCHERS,
                     message_thread_id=threadId, reply_markup=inline_to_talk)
    bot.edit_forum_topic(Config.FORUM_CHAT, threadId, icon_custom_emoji_id=Emoji.CLOSED_TASK)

@maybeTopicNotExistsDecorator
def forwardRate(threadId, rate):
    bot.send_message(Config.FORUM_CHAT, Replicas.TASK_RATE_TOPIC_WATCHERS + str(rate), message_thread_id=threadId)
    bot.send_message(Config.FORUM_CHAT,
                     Replicas.TASK_RATE_GENERAL_WATCHERS + str(rate) + '\n' + Replicas.LINK_TO_TOPIC.format(
                         linkToTopic(threadId)), parse_mode='HTML')  # TODO make link to topic

@maybeTopicNotExistsDecorator
def forwardMessage(threadId: int, msg: telebot.types.Message):
    if msg.content_type == 'media_group':
        msgIds = list(map(lambda p: p[1], msg.photo))
        bot.forward_messages(Config.FORUM_CHAT, msg.chat.id, msgIds, message_thread_id=threadId)
    else:
        bot.forward_message(Config.FORUM_CHAT, msg.chat.id, msg.id, message_thread_id=threadId)

@maybeTopicNotExistsDecorator
def forwardRedir(threadId: int, consultant: str, pointCity: str, pointName: str,
                 postMsg):  # TODO send new post text
    bot.send_message(Config.FORUM_CHAT,
                     Replicas.TASK_REDIRECT_WATCHERS.format(consultant=consultant, newCity=pointCity,
                                                            newGroup=pointName),
                     message_thread_id=threadId)
    forwardMessage(threadId, postMsg)
