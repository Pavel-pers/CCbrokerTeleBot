import threading
import queue
import telebot
import logging

from constants import *
from locLibs import dbFunc
from locLibs import simpleClasses
from locLibs import botTools
from handlers.inlineCallBacks import addCbData
from handlers.decorators import threaded, photoGrouping
from handlers import threadWorker

clientLock = threaded.InProcHandlers()


class TaskHandlers(simpleClasses.Handlers):
    def __init__(self):
        super().__init__()

    # telegram side
    def catchChannelMsg(self, msg: telebot.types.Message):
        originGr = msg.forward_origin.chat.id
        originId = msg.forward_origin.message_id
        curGr = msg.chat.id
        curId = msg.message_id
        self.logger.debug(
            f'catched telegram msg: {repr(msg.text)}. {originGr}, {originId}, changing on: {curGr}, {curId}')
        dbFunc.changeTaskPost(originGr, originId, curGr, curId)
        botTools.processComments(originGr, originId, curGr, curId)

    # client side
    #   -client hasn't answer inline question
    def askToAnswerInline(self, msg: telebot.types.Message, prevMsgId):
        inline = telebot.types.InlineKeyboardMarkup()
        inline.add(telebot.types.InlineKeyboardButton(text='cancel', callback_data=Inline.POST_CANCEL))
        reply = None
        try:
            reply = self.bot.send_message(msg.chat.id, 'please answer previous question, or press button bellow',
                                          reply_markup=inline, reply_to_message_id=prevMsgId)
        except telebot.apihelper.ApiTelegramException:  # this may process if only message doesn't exist
            reply = self.bot.send_message(msg.chat.id, 'please answer previous question, or press button bellow',
                                          reply_markup=inline)
        self.bot.register_next_step_handler(
            reply, lambda recMsg: clientQ.put((self.askToAnswerInline, (recMsg,))), prevMsgId)

    #   -process first message from client
    def handleStartConversation(self, msg: telebot.types.Message):
        client = dbFunc.getClientById(msg.from_user.id)
        if client is None:  # client has skipped the registration
            self.bot.send_message(msg.chat.id, 'please enter /start for register')
            return

        inlineKeyboard = telebot.types.InlineKeyboardMarkup()  # make keyboard
        cancelBtn = telebot.types.InlineKeyboardButton('cancel', callback_data=Inline.POST_CANCEL)
        continueBtn = telebot.types.InlineKeyboardButton('continue', callback_data=Inline.POST_CONTINUE)
        inlineKeyboard.add(cancelBtn, continueBtn)
        pointName = dbFunc.getPointById(client[3])[2]

        reply = self.bot.send_message(msg.chat.id, f'your city = {client[2]}, point = {pointName}, continue?',
                                      reply_markup=inlineKeyboard)
        self.bot.register_next_step_handler_by_chat_id(
            reply.chat.id, lambda recMsg: clientQ.put((self.askToAnswerInline, (recMsg,))), reply.id)  # reg waiting

        shrinkedMsg = simpleClasses.MsgContent(msg)
        addCbData((reply.chat.id, None), (client, shrinkedMsg))

    #   -client add message to existing task
    def handleClientSide(self, msg: telebot.types.Message, taskInfo):
        client, group, postId = taskInfo[:3]  # skips birth info
        cbList = botTools.redirectMsg(msg, '-client answer-')
        botTools.addComment(group, postId, cbList)

    #   - entry point
    @threaded.thread_friendly(clientLock, lambda args: args[1].chat.id)
    def handleClient(self, msg: telebot.types.Message):
        self.logger.debug('begin processing msg from client:' + str(msg.chat.id))
        taskInfo = dbFunc.getTaskByClientId(msg.from_user.id)
        if taskInfo is None:
            self.handleStartConversation(msg)
        else:
            self.handleClientSide(msg, taskInfo)
        self.logger.debug('end processing msg from client:' + str(msg.chat.id))

    # consultant side
    #   -redir functions
    def redirectClientGen(self, msg: telebot.types.Message, client):
        postMsg = msg.reply_to_message
        clientId, clientName, clientCity, clientBind = client
        self.bot.send_message(clientId, 'you gonna redirect')

        cityList = dbFunc.getRegCityList()
        reply = self.bot.reply_to(postMsg, 'say about /cancel, ask about city\ncities:\n' + '\n'.join(cityList))

        pointList = []
        newCity = ''
        while len(pointList) == 0:
            msg = yield reply, False  # waiting for city

            while msg.text != '/cancel' and msg.text not in cityList:
                reply = self.bot.reply_to(postMsg, 'incorrect city')
                msg = yield reply, False

            if msg.text == '/cancel':
                self.bot.send_message(clientId, 'redirection has stoped')
                yield reply, True

            newCity = msg.text
            # get point list
            pointList = dbFunc.getPointsByCity(newCity)
            if clientCity == newCity:
                pointList.remove(next(i for i in pointList if i[0] == postMsg.chat.id))

            if len(pointList) == 0:
                self.bot.reply_to(postMsg, 'there are no suitable points')

        pointNameList = list(map(lambda x: x[2], pointList))
        reply = self.bot.reply_to(postMsg, 'ask about point\npoints:\n' + '\n'.join(pointNameList))

        msg = yield reply, False  # waiting for point
        while msg.text != '/cancel' and msg.text not in pointNameList:
            reply = self.bot.reply_to(postMsg, 'incorrect point')
            msg = yield reply, False

        if msg.text == '/cancel':
            self.bot.send_message(clientId, 'redirection has stoped')
            yield reply, True

        newPoint = next(i[0] for i in pointList if i[2] == msg.text)

        reply = self.bot.reply_to(postMsg, 'ask about post text')
        msg = yield reply, False  # waiting for post text

        if msg.text == '/cancel':
            self.bot.send_message(clientId, 'redirection has stoped')
            yield reply, True

        self.bot.send_message(clientId, 'redirect successfully')
        reply = self.bot.reply_to(postMsg, 'redirect successfully')

        dbFunc.delTask(clientId)
        dbFunc.changeClientBind(clientId, newCity, newPoint)
        newClient = (client[0], client[1], newCity, newPoint)
        botTools.addNewTask(newClient, msg)
        yield reply, True

    def redirectClient(self, msg: telebot.types.Message, clientId, gen):
        post = msg.reply_to_message
        reply, stop = gen.send(msg)
        if not stop:
            self.bot.register_for_reply(
                post, lambda recMsg: cosultantQ.put((self.redirectClient, (recMsg,))), clientId, gen)
        else:
            self.bot.delete_state(clientId)

    #   -entry point
    def handleConsultant(self, msg: telebot.types.Message):
        postMsg = msg.reply_to_message
        replyChat = postMsg.chat.id
        replyId = postMsg.message_id
        self.logger.debug('processing comment: chat' + str(replyChat) + ',post' + str(replyId))

        consultant = dbFunc.getConsultantById(msg.from_user.id)
        if consultant is None:  # consultant has skiped the registration
            self.bot.send_message(msg.chat.id, 'please enter /set_name <NAME> for register')
            return

        task = dbFunc.getTaskByPost(replyChat, replyId)
        if task is None:
            self.bot.reply_to(postMsg, 'this post is not supported')
            return

        clientId = task[0]
        clientState = self.bot.get_state(clientId)
        if clientState == UserStages.CLIENT_REDIR:
            return

        if msg.text == '/close':
            botTools.endTask(clientId)
        elif msg.text == '/ban':
            dbFunc.delTask(clientId)
            dbFunc.delClient(clientId)
            self.bot.send_message(clientId, 'you have banned!')
            self.bot.reply_to(postMsg, 'banned')
            botTools.blockUser(clientId)
        elif msg.text == '/redirect':
            self.bot.set_state(clientId, UserStages.CLIENT_REDIR)

            client = dbFunc.getClientById(clientId)
            redirProc = self.redirectClientGen(msg, client)
            reply, stop = next(redirProc)
            if not stop:
                self.logger.debug('register redirect sess on: ' + str(replyChat) + '-' + str(replyId))
                self.bot.register_for_reply(
                    postMsg, lambda recMsg: cosultantQ.put((self.redirectClient, (recMsg,))), clientId, redirProc)
        else:
            dbFunc.addNewActive(clientId, consultant[0])
            cbList = botTools.redirectMsg(msg, 'consultant name: ' + consultant[1])
            for cb in cbList:
                cb(clientId, None)


handlers = TaskHandlers()
clientQ = queue.Queue()
cosultantQ = queue.Queue()


def startListenClient(bot: telebot.TeleBot, botLogger: logging.Logger, ignoreErrs=False):
    # set up handlers and thread pool
    handlers.set_bot(bot)
    handlers.set_logger(botLogger)

    workerPool = [threading.Thread(target=threadWorker.worker, args=(clientQ, botLogger, ignoreErrs)) for i in range(5)]
    for i in workerPool:
        i.start()

    # add handlers to telebot
    @bot.message_handler(func=lambda message: message.from_user.id == 777000 and botTools.isMsgFromPoint(message),
                         content_types=Config.ALLOWED_CONTENT)
    def catchProducer(msg: telebot.types.Message):
        clientQ.put((handlers.catchChannelMsg, (msg,)))

    @bot.message_handler(func=lambda message: message.chat.type == 'private', content_types=Config.ALLOWED_CONTENT)
    @photoGrouping.decorator
    def clientProducer(msg: telebot.types.Message):
        clientQ.put((handlers.handleClient, (msg,)))


def startListenConsultant(bot: telebot.TeleBot, botLogger: logging.Logger, ignoreErrs=False):
    # set up handlers and thread pool
    handlers.set_bot(bot)
    handlers.set_logger(botLogger)

    workerPool = [threading.Thread(target=threadWorker.worker, args=(cosultantQ, botLogger, ignoreErrs))
                  for i in range(3)]
    for i in workerPool:
        i.start()

    # add handlers to telebot

    @bot.message_handler(func=botTools.isPostReply, content_types=Config.ALLOWED_CONTENT)
    @photoGrouping.decorator
    def consultantProducer(msg: telebot.types.Message):
        cosultantQ.put((handlers.handleConsultant, (msg,)))
