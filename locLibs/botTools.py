from datetime import datetime
import telebot
from telebot.types import KeyboardButton

from locLibs import dbFunc
from locLibs import simpleClasses
from handlers.inlineCallBacks import addCbData
from constants import Emoji, Inline, FORUM_CHAT

bot: telebot.TeleBot


def blockUser(userId):
    bot.block_user(userId)
    dbFunc.addBlockUser(userId)


def isMsgFromPoint(msg: telebot.types.Message):
    return msg.chat.type in ['supergroup', 'channel'] and dbFunc.getPointById(
        msg.chat.id) is not None or dbFunc.getPointById(
        bot.get_chat(msg.chat.id).linked_chat_id) is not None


def redirectMsg(msg: telebot.types.Message, header):
    text = msg.text or msg.caption or ''
    text = header + '\n' + text

    if msg.content_type == 'text':
        return (lambda ch, repl: bot.send_message(ch, text, reply_to_message_id=repl),)
    if msg.content_type == 'photo':  # TODO make photos grouping
        return (lambda ch, repl: bot.send_photo(ch, msg.photo[0].file_id, caption=text, reply_to_message_id=repl),)
    if msg.content_type == 'document':
        return (lambda ch, repl: bot.send_document(ch, msg.document.file_id, caption=text, reply_to_message_id=repl),)
    if msg.content_type == 'audio':
        return (lambda ch, repl: bot.send_audio(ch, msg.audio.file_id, caption=text, reply_to_message_id=repl),)
    if msg.content_type == 'video':
        return (lambda ch, repl: bot.send_video(ch, msg.video.file_id, caption=text, reply_to_message_id=repl),)
    if msg.content_type == 'voice':
        return (lambda ch, repl: bot.send_voice(ch, msg.voice.file_id, caption=text, reply_to_message_id=repl),)
    if msg.content_type == 'video_note':
        return (lambda ch, repl: bot.send_message(ch, header + '\nsent a video note', reply_to_message_id=repl),
                lambda ch, repl: bot.send_video_note(ch, msg.video_note.file_id, reply_to_message_id=repl))
    if msg.content_type == 'sticker':
        return (lambda ch, repl: bot.send_message(ch, header + '\nsent a sticker', reply_to_message_id=repl),
                lambda ch, repl: bot.send_sticker(ch, msg.sticker.file_id, reply_to_message_id=repl))
    if msg.content_type == 'media_group':
        photos = list(map(lambda p: p[0], msg.photo))
        photos[0].caption = header + '\n' + (photos[0].caption or '')
        return (lambda ch, repl: bot.send_media_group(ch, photos, reply_to_message_id=repl),)


def isFromAdmin(msg: telebot.types.Message):
    return bot.get_chat_member(msg.chat.id, msg.from_user.id).status in ['administrator', 'creator']


def waitRelpyFromAdmin(reply, stopReg):
    msg = yield reply, stopReg
    while not isFromAdmin(msg):
        reply = bot.send_message(msg.chat.id, 'you are not admin..')
        msg = yield reply, False
    return msg


def askWithKeyboard(chatId, header: str, answerList: list, onlyAdmin: bool):  # !use only with generators
    keyboard = telebot.types.ReplyKeyboardMarkup()
    text = header + '\n'
    for i in range(len(answerList)):
        text += str(i + 1) + ': ' + answerList[i] + '\n'
        keyboard.add(answerList[i])

    reply = bot.send_message(chatId, text, reply_markup=keyboard)

    answer = ''
    while answer not in answerList and not (answer.isdigit() and 0 < int(answer) <= len(answerList)):
        if answer:
            reply = bot.send_message(chatId, 'incorect format', reply_markup=keyboard)

        if onlyAdmin:
            msg = yield from waitRelpyFromAdmin(reply, False)
        else:
            msg = yield reply, False
        answer = msg.text

    return int(answer) - 1 if answer.isdigit() else answerList.index(answer)


def isPostReply(msg: telebot.types.Message):
    return msg.reply_to_message is not None and msg.reply_to_message.from_user.id == 777000 and isMsgFromPoint(msg)


# task funcs
pendingPostMsgs = simpleClasses.PendingMessages()  # messages which waiting telegramm repeat


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
    header = 'name:' + clientName + ', city:' + clientCity

    cbList = redirectMsg(postMsg, header)
    post = cbList[0](clientChannel, None)
    replyId = post.message_id if type(post) is telebot.types.Message else post[0].message_id  # check on media group
    pendingPostMsgs.newAwait(clientChannel, replyId)
    for i in cbList[1:]:
        pendingPostMsgs.add(clientChannel, replyId, i)
    return clientChannel, replyId


#   -delete data in DB and ask client
def endTask(clientId):
    # TODO ask for rate
    inline = telebot.types.InlineKeyboardMarkup(row_width=5)
    for i in range(1, 6):
        inline.add(telebot.types.InlineKeyboardButton(Emoji.RATE[i], callback_data=Inline.RATE_PREF + str(i)))

    reply = bot.send_message(clientId, 'the end of conversation, please rate', reply_markup=inline)
    task = dbFunc.getTaskByClientId(clientId)
    activeIds = task[4].split(';')[:-1]
    topicId = task[3]
    addCbData((clientId, reply.message_id), activeIds + [topicId])
    bot.delete_state(clientId)
    dbFunc.delTask(clientId)


# forwarding func
#   -open task, forum
def startFrorward(clientCity: str, clientName: str, pointName):
    time = datetime.today().strftime('%m/%d %H:%M"')
    topic = bot.create_forum_topic(FORUM_CHAT, f'{clientCity} [{time}] from {clientName}',
                                   icon_custom_emoji_id=Emoji.OPEN_TASK)
    bot.send_message(FORUM_CHAT, 'client sent message to:' + pointName, message_thread_id=topic.message_thread_id)
    return topic.message_thread_id


def endFrorward(threadId, fromClient: bool):
    bot.send_message(FORUM_CHAT, 'task closed by ' + ('client' if fromClient else 'consultant'),
                     message_thread_id=threadId)
    bot.edit_forum_topic(FORUM_CHAT, threadId, icon_custom_emoji_id=Emoji.CLOSED_TASK)


def forwardRate(threadId, rate):
    bot.send_message(FORUM_CHAT, 'rate:' + str(rate), message_thread_id=threadId)
    bot.send_message(FORUM_CHAT, 'new rate:' + str(rate))  # TODO make link to topic


def forwardMessage(threadId: int, msg: telebot.types.Message):
    if msg.content_type == 'media_group':
        msgIds = list(map(lambda p: p[1], msg.photo))
        bot.forward_messages(FORUM_CHAT, msg.chat.id, msgIds, message_thread_id=threadId)
    else:
        bot.forward_message(FORUM_CHAT, msg.chat.id, msg.id, message_thread_id=threadId)


def forwardRedir(threadId: int, consutant: str, pointCity: str, pointName: str, postMsg):  # TODO send new post text
    bot.send_message(FORUM_CHAT, f'{consutant} redirect client\n To city:{pointCity} name:{pointName}\nnew msg:',
                     message_thread_id=threadId)
    forwardMessage(threadId, postMsg)
