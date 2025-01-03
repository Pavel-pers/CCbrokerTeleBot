import telebot
import logging

from constants import Config, Inline, Replicas, UserStages
from locLibs import dbFunc, simpleClasses, botTools, simpleTools, reminders
from handlers.inlineCallBacks import addCbData
from handlers.decorators import photoGrouping, processOnce
from handlers import threadWorker


def handleClientSide(msg: telebot.types.Message, taskInfo):
    client, group, postId = taskInfo[:3]
    cbList = botTools.redirectMsg(msg, Replicas.CLENT_ANSWER)
    botTools.addComment(group, postId, cbList)
    botTools.forwardMessage(taskInfo[3], msg)


class ClientHandlers(simpleClasses.Handlers):
    # telegram side
    def catchChannelMsg(self, msg: telebot.types.Message):
        originGr = msg.forward_origin.chat.id
        originId = msg.forward_origin.message_id
        curGr = msg.chat.id
        curId = msg.message_id
        self.logger.debug(
            f'catched telegram msg: {repr(msg.text)}. {originGr}, {originId}, changing on: {curGr}, {curId}')
        dbFunc.changeTaskByPost(originGr, originId, curGr, curId)
        botTools.processComments(originGr, originId, curGr, curId)

    # client side
    #   -client hasn't answered inline question
    def answerInlineProducer(self, msg, prevMsgId):
        self.putTask(self.askToAnswerInline, (msg, prevMsgId))

    def askToAnswerInline(self, msg: telebot.types.Message, prevMsgId):
        inline = telebot.types.InlineKeyboardMarkup()
        inline.add(telebot.types.InlineKeyboardButton(text=Replicas.CANCEL_BUTTON, callback_data=Inline.POST_CANCEL))
        try:
            reply = self.bot.send_message(msg.chat.id, Replicas.ASK_TO_ASNWER_BELLOW,
                                          reply_markup=inline, reply_to_message_id=prevMsgId)
        except telebot.apihelper.ApiTelegramException:  # this may process if only message doesn't exist
            reply = self.bot.send_message(msg.chat.id, Replicas.ASK_TO_ASNWER_BELLOW,
                                          reply_markup=inline)
        self.bot.register_next_step_handler(
            reply, self.answerInlineProducer, prevMsgId)

    #   -process first message from client
    def handleStartConversation(self, msg: telebot.types.Message):
        client = dbFunc.getClientById(msg.from_user.id)
        if client is None:  # client has skipped the registration
            self.bot.send_message(msg.chat.id, Replicas.WELCOME_CLIENT)
            return

        inlineKeyboard = telebot.types.InlineKeyboardMarkup()  # make keyboard
        cancelBtn = telebot.types.InlineKeyboardButton(Replicas.CANCEL_BUTTON, callback_data=Inline.POST_CANCEL)
        continueBtn = telebot.types.InlineKeyboardButton(Replicas.CONTINUE_BUTTON, callback_data=Inline.POST_CONTINUE)
        inlineKeyboard.add(cancelBtn, continueBtn)
        pointInfo = dbFunc.getPointById(client[3])
        pointName = pointInfo[2]
        workH = pointInfo[3]

        dist = simpleTools.distToTimeSgm(workH)
        confirmText = Replicas.gen_confirm_text(pointInfo[1], pointName, dist)
        reply = self.bot.send_message(msg.chat.id, confirmText, reply_markup=inlineKeyboard, parse_mode='HTML')

        self.bot.register_next_step_handler_by_chat_id(
            reply.chat.id, self.answerInlineProducer, reply.id)  # reg waiting

        shrinkedMsg = simpleClasses.MsgContent(msg)
        addCbData((reply.chat.id, None), (client, pointName, shrinkedMsg))

    #   -client add message to existing task

    #   - entry point
    def handleClient(self, msg: telebot.types.Message):
        self.logger.debug('begin processing msg from client:' + str(msg.chat.id))
        taskInfo = dbFunc.getTaskByClientId(msg.from_user.id)
        if taskInfo is None:
            endTaskInfo = dbFunc.getClosedTaskByClientId(msg.from_user.id)
            if endTaskInfo is None:
                self.handleStartConversation(msg)
            else: # * watcher reflection
                topicId = endTaskInfo[0]
                botTools.forwardMessage(topicId, msg)
        else:
            handleClientSide(msg, taskInfo)
        self.logger.debug('end processing msg from client:' + str(msg.chat.id))


class ConsultantHandlers(simpleClasses.Handlers):
    def __init__(self):
        super().__init__()

    #   -redirect functions
    def redirectClientGen(self, msg: telebot.types.Message, client, consultantName, topicId):
        msg: telebot.types.Message

        postMsg = msg.reply_to_message
        clientId, clientName, clientCity, clientBind = client
        self.bot.send_message(clientId, Replicas.ON_CLIENT_REDIRECTION)

        answersList: list = dbFunc.getRegCities()
        answersList.append('/cancel')
        pointList = []
        newCity = ''
        while not pointList:
            cityIndex = yield from botTools.askToChoice(postMsg.chat.id, postMsg.id, None,
                                                        Replicas.SAY_ABOUT_CANCEL + '\n\n' + Replicas.ASK_ABOUT_REDIRECT_CITY,
                                                        answersList, False)
            if cityIndex == len(answersList) - 1:
                self.bot.send_message(clientId, Replicas.ON_REDIRECTTION_STOP)
                reply = self.bot.reply_to(postMsg, Replicas.ON_REDIRECTTION_STOP)
                yield reply, True

            newCity = answersList[cityIndex]

            pointList = dbFunc.getPointsByCity(newCity)
            if clientCity == newCity:
                pointList.remove(next(i for i in pointList if i[0] == postMsg.chat.id))

            if len(pointList) == 0:
                self.bot.reply_to(postMsg, Replicas.NO_SUITABLE_POINTS)

        answersList = list(map(lambda x: x[2], pointList))
        answersList.append('/cancel')

        pointIndx = yield from botTools.askToChoice(msg.chat.id, postMsg.id, None, Replicas.ASK_ABOUT_REDIRECT_POINT,
                                                    answersList, False)
        if pointIndx == len(answersList) - 1:
            self.bot.send_message(clientId, Replicas.ON_REDIRECTTION_STOP)
            reply = self.bot.reply_to(postMsg, Replicas.ON_REDIRECTTION_STOP)
            yield reply, True

        pointName = answersList[pointIndx]
        newPoint = pointList[pointIndx]

        reply = self.bot.reply_to(postMsg, Replicas.ASK_ABOUT_REDIRECT_TEXT)
        msg = yield reply, False  # waiting for post msg

        if msg.text == '/cancel':
            self.bot.send_message(clientId, Replicas.ON_REDIRECTTION_STOP)
            reply = self.bot.reply_to(postMsg, Replicas.ON_REDIRECTTION_STOP)
            yield reply, True

        self.bot.send_message(clientId, Replicas.SUCSESS_REDIRECT)
        reply = self.bot.reply_to(postMsg, Replicas.SUCSESS_REDIRECT)

        dbFunc.changeClientBind(clientId, newCity, newPoint[0])
        newClient = (client[0], client[1], newCity, newPoint[0])
        newCh, newPostId = botTools.addNewTask(newClient, msg)
        dbFunc.changeTaskByPost(msg.chat.id, postMsg.id, newCh, newPostId)
        botTools.forwardRedir(topicId, consultantName, newCity, pointName, msg)
        reminders.delReminder(msg.chat.id, clientId)
        reminders.regReminder(newPoint[0], clientId, clientName)
        yield reply, True

    def redirectClient(self, msg: telebot.types.Message, clientId, gen):
        post = msg.reply_to_message
        reply, stop = gen.send(msg)
        if not stop:
            self.bot.register_for_reply(post, self.redirProducer, clientId, gen)
        else:
            self.bot.delete_state(clientId)
            self.bot.set_state(clientId, UserStages.CLIENT_IN_CONVERSATION)

    @processOnce.getDecorator(keyInd=1)
    @photoGrouping.getDecorator(msgParamIndx=1)
    def redirProducer(self, *args):
        self.putTask(self.redirectClient, args)

    #   -entry point
    def handleConsultant(self, msg: telebot.types.Message):
        postMsg = msg.reply_to_message
        replyChat = postMsg.chat.id
        replyId = postMsg.message_id
        self.logger.debug('processing comment: chat' + str(replyChat) + ',post' + str(replyId))

        if not botTools.is_member(self.bot.get_chat_member(msg.chat.id, msg.from_user.id)):
            self.bot.reply_to(postMsg, Replicas.ASK_TO_JOIN_GROUP)
            return

        consultant = dbFunc.getConsultantById(msg.from_user.id)
        if consultant is None:  # consultant has skiped the registration
            self.logger.warning("no consultant found")
            self.bot.reply_to(postMsg, Replicas.ASK_NAME_CONSULTANT)
            return

        task = dbFunc.getTaskByPost(replyChat, replyId)
        if task is None:
            self.bot.reply_to(postMsg, Replicas.ON_NOT_SUPPORTED_TASK)
            return

        clientId = task[0]
        clientState = self.bot.get_state(clientId)
        if clientState == UserStages.CLIENT_REDIR:
            return

        if msg.text == '/close':
            reminders.delReminder(replyChat, clientId)
            botTools.forwardMessage(task[3], msg)
            botTools.endFrorward(task[3], clientId)

            botTools.endTask(clientId)
        elif msg.text == '/ban':
            reminders.delReminder(replyChat, clientId)
            botTools.forwardMessage(task[3], msg)
            botTools.endFrorward(task[3], clientId)

            dbFunc.delTask(clientId)
            dbFunc.delClient(clientId)
            self.bot.send_message(clientId, Replicas.BANNED_TEXT)
            self.bot.reply_to(postMsg, 'banned')
            botTools.blockUser(clientId)
        elif msg.text == '/redirect':
            self.bot.set_state(clientId, UserStages.CLIENT_REDIR)

            client = dbFunc.getClientById(clientId)
            redirProc = self.redirectClientGen(msg, client, consultant[1], task[3])
            reply, stop = next(redirProc)
            if not stop:
                self.logger.debug('register redirect sess on: ' + str(replyChat) + '-' + str(replyId))
                self.bot.register_for_reply(postMsg, self.redirProducer, clientId, redirProc)
            else:
                self.bot.delete_state(clientId)
                self.bot.set_state(clientId, UserStages.CLIENT_IN_CONVERSATION)
        else:
            reminders.markReminder(replyChat, clientId)
            botTools.forwardMessage(task[3], msg)
            dbFunc.addNewActive(clientId, consultant[0])

            cbList = botTools.redirectMsg(msg, Replicas.CONSULTANT_ANSWER + consultant[1])
            for cb in cbList:
                cb(clientId, None)


handlersCo = ConsultantHandlers()  # using cos = client side
handlersCl = ClientHandlers()  # using cls = consultant side


def startListenClient(bot: telebot.TeleBot, botLogger: logging.Logger, ignoreErrs=False):
    # set up handlers and thread pool
    pool = threadWorker.PoolHandlers(5, botLogger, ignoreErrs, lambda msg, *args: msg.chat.id % 5,
                                     handler_name="TaskClsHandler")
    handlersCl.set_bot(bot)
    handlersCl.set_logger(botLogger)
    handlersCl.set_work_queue_interactor(pool.addTask)

    # add handlers to telebot
    bot.message_handler(func=lambda message: message.from_user.id == 777000 and botTools.isMsgFromPoint(message),
                        content_types=Config.ALLOWED_CONTENT)(
        pool.handlerDecorator(
            handlersCl.catchChannelMsg
        )
    )

    bot.message_handler(func=lambda message: message.chat.type == 'private', content_types=Config.ALLOWED_CONTENT)(
        photoGrouping.getDecorator()(
            pool.handlerDecorator(
                handlersCl.handleClient
            )
        )
    )


def startListenConsultant(bot: telebot.TeleBot, botLogger: logging.Logger, ignoreErrs=False):
    # set up handlers and thread pool
    pool = threadWorker.PoolHandlers(3, botLogger, ignoreErrs, lambda msg, *args: msg.chat.id % 3,
                                     handler_name="TaskCosHandler")
    handlersCo.set_bot(bot)
    handlersCo.set_logger(botLogger)
    handlersCo.set_work_queue_interactor(pool.addTask)
    # add handlers to telebot

    bot.message_handler(func=botTools.isPostReply, content_types=Config.ALLOWED_CONTENT)(
        processOnce.getDecorator()(
            photoGrouping.getDecorator()(
                pool.handlerDecorator(
                    handlersCo.handleConsultant
                )
            )
        )
    )
