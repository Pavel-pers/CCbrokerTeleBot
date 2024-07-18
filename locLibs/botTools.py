import telebot
from locLibs import dbFunc
from locLibs import simpleClasses

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


def waitRelpyFromAdmin(reply, stopReg):
    msg = yield reply, stopReg
    while bot.get_chat_member(msg.chat.id, msg.from_user.id).status not in ['administrator', 'creator']:
        reply = bot.send_message(msg.chat.id, 'you are not admin..')
        msg = yield reply, False
    return msg


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
    pendingPostMsgs.newAwait(clientChannel, post.message_id)
    for i in cbList[1:]:
        pendingPostMsgs.add(clientChannel, post.message_id, i)
    dbFunc.addNewTask(clientId, clientChannel, post.message_id)


#   -delete data in DB and ask client
def endTask(clientId):
    # TODO ask for rate
    bot.delete_state(clientId)
    bot.send_message(clientId, 'the end of conversation')
    dbFunc.delTask(clientId)
