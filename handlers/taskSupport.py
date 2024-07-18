import logging
import telebot
from constants import *
from locLibs import dbFunc
from locLibs import simpleClasses
import locLibs.botTools as botTools
from handlers.inlineCallBacks import addCbData


def startListenClient(bot: telebot.TeleBot, botLogger: logging.Logger):
    # -handle repeat message from telegram
    @bot.message_handler(func=lambda message: message.from_user.id == 777000 and botTools.isMsgFromPoint(message),
                         content_types=Config.ALLOWED_CONTENT)
    def catchChannelMsg(msg: telebot.types.Message):
        originGr = msg.forward_origin.chat.id
        originId = msg.forward_origin.message_id
        curGr = msg.chat.id
        curId = msg.message_id
        botLogger.debug(
            f'catched telegram msg: {repr(msg.text)}. {originGr}, {originId}, changing on: {curGr}, {curId}')
        dbFunc.changeTaskPost(originGr, originId, curGr, curId)
        botTools.processComments(originGr, originId, curGr, curId)

    def askToAnswerInline(msg: telebot.types.Message, prevMsgId):
        inline = telebot.types.InlineKeyboardMarkup()
        inline.add(telebot.types.InlineKeyboardButton(text='cancel', callback_data=Inline.POST_CANCEL))
        reply = None
        try:
            reply = bot.send_message(msg.chat.id, 'please answer previous question, or press button bellow',
                                     reply_markup=inline, reply_to_message_id=prevMsgId)
        except telebot.apihelper.ApiTelegramException:  # this may process if only message doesn't exist
            reply = bot.send_message(msg.chat.id, 'please answer previous question, or press button bellow',
                                     reply_markup=inline)
        bot.register_next_step_handler(reply, askToAnswerInline, prevMsgId)

    def handleStartConversation(msg: telebot.types.Message):
        client = dbFunc.getClientById(msg.from_user.id)
        if client is None:  # client has skipped the registration
            bot.send_message(msg.chat.id, 'please enter /start for register')
            return

        inlineKeyboard = telebot.types.InlineKeyboardMarkup()  # make keyboard
        cancelBtn = telebot.types.InlineKeyboardButton('cancel', callback_data=Inline.POST_CANCEL)
        continueBtn = telebot.types.InlineKeyboardButton('continue', callback_data=Inline.POST_CONTINUE)
        inlineKeyboard.add(cancelBtn, continueBtn)
        pointName = dbFunc.getPointById(client[3])[2]

        reply = bot.send_message(msg.chat.id, f'your city = {client[2]}, point = {pointName}, continue?',
                                 reply_markup=inlineKeyboard)
        bot.register_next_step_handler_by_chat_id(reply.chat.id, askToAnswerInline, reply.id)  # reg waiting

        shrinkedMsg = simpleClasses.MsgContent(msg)
        addCbData((reply.chat.id, None), (client, shrinkedMsg))

    #       -client add message to existing task
    def handleClientSide(msg: telebot.types.Message, taskInfo):
        client, group, postId = taskInfo[:3]  # skips birth info
        cbList = botTools.redirectMsg(msg, '-client answer-')
        botTools.addComment(group, postId, cbList)

    #       -handle new message from client
    @bot.message_handler(func=lambda message: message.chat.type == 'private', content_types=Config.ALLOWED_CONTENT)
    def handleClient(msg: telebot.types.Message):
        botLogger.debug('begin processing msg from client:' + str(msg.chat.id))
        taskInfo = dbFunc.getTaskByClientId(msg.from_user.id)
        if taskInfo is None:
            handleStartConversation(msg)
        else:
            handleClientSide(msg, taskInfo)
        botLogger.debug('end processing msg from client:' + str(msg.chat.id))


def startListenConsultant(bot: telebot.TeleBot, botLogger: logging.Logger):
    # redir functions
    def redirectClientGen(msg: telebot.types.Message, client):
        postMsg = msg.reply_to_message
        clientId, clientName, clientCity, clientBind = client
        bot.send_message(clientId, 'you gonna redirect')

        cityList = dbFunc.getRegCityList()
        reply = bot.reply_to(postMsg, 'say about /cancel, ask about city\ncities:\n' + '\n'.join(cityList))

        pointList = []
        newCity = ''
        while len(pointList) == 0:
            msg = yield reply, False  # waiting for city

            while msg.text != '/cancel' and msg.text not in cityList:
                reply = bot.reply_to(postMsg, 'incorrect city')
                msg = yield reply, False

            if msg.text == '/cancel':
                bot.send_message(clientId, 'redirection has stoped')
                yield reply, True

            newCity = msg.text
            # get point list
            pointList = dbFunc.getPointsByCity(newCity)
            if clientCity == newCity:
                pointList.remove(next(i for i in pointList if i[0] == postMsg.chat.id))

            if len(pointList) == 0:
                bot.reply_to(postMsg, 'there are no suitable points')

        pointNameList = list(map(lambda x: x[2], pointList))
        reply = bot.reply_to(postMsg, 'ask about point\npoints:\n' + '\n'.join(pointNameList))

        msg = yield reply, False  # waiting for point
        while msg.text != '/cancel' and msg.text not in pointNameList:
            reply = bot.reply_to(postMsg, 'incorrect point')
            msg = yield reply, False

        if msg.text == '/cancel':
            bot.send_message(clientId, 'redirection has stoped')
            yield reply, True

        newPoint = next(i[0] for i in pointList if i[2] == msg.text)

        reply = bot.reply_to(postMsg, 'ask about post text')
        msg = yield reply, False  # waiting for post text

        if msg.text == '/cancel':
            bot.send_message(clientId, 'redirection has stoped')
            yield reply, True

        bot.send_message(clientId, 'redirect successfully')
        reply = bot.reply_to(postMsg, 'redirect successfully')

        dbFunc.delTask(clientId)
        dbFunc.changeClientBind(clientId, newCity, newPoint)
        newClient = (client[0], client[1], newCity, newPoint)
        botTools.addNewTask(newClient, msg)
        yield reply, True

    def redirectClient(msg: telebot.types.Message, clientId, gen):
        post = msg.reply_to_message
        reply, stop = gen.send(msg)
        if not stop:
            bot.register_for_reply(post, redirectClient, clientId, gen)
        else:
            bot.delete_state(clientId)

        #       -handler consultant messages, ignore redireced sessions

    @bot.message_handler(func=botTools.isPostReply, content_types=Config.ALLOWED_CONTENT)
    def handleConsultant(msg: telebot.types.Message):
        postMsg = msg.reply_to_message
        replyChat = postMsg.chat.id
        replyId = postMsg.message_id
        botLogger.debug('processing comment: chat' + str(replyChat) + ',post' + str(replyId))

        consultant = dbFunc.getConsultantById(msg.from_user.id)
        if consultant is None:  # consultant has skiped the registration
            bot.send_message(msg.chat.id, 'please enter /set_name <NAME> for register')
            return

        task = dbFunc.getTaskByPost(replyChat, replyId)
        if task is None:
            bot.reply_to(postMsg, 'this post is not supported')
            return

        clientId = task[0]
        clientState = bot.get_state(clientId)
        if clientState == UserStages.CLIENT_REDIR:
            return

        if msg.text == '/close':
            botTools.endTask(clientId)
        elif msg.text == '/ban':
            dbFunc.delTask(clientId)
            dbFunc.delClient(clientId)
            bot.send_message(clientId, 'you have banned!')
            bot.reply_to(postMsg, 'banned')
            botTools.blockUser(clientId)
        elif msg.text == '/redirect':
            bot.set_state(clientId, UserStages.CLIENT_REDIR)

            client = dbFunc.getClientById(clientId)
            redirProc = redirectClientGen(msg, client)
            reply, stop = next(redirProc)
            if not stop:
                botLogger.debug('register redirect sess on: ' + str(replyChat) + '-' + str(replyId))
                bot.register_for_reply(postMsg, redirectClient, clientId, redirProc)
        else:
            cbList = botTools.redirectMsg(msg, 'consultant name: ' + consultant[1])
            for cb in cbList:
                cb(clientId, None)
