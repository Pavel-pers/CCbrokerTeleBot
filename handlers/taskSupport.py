import telebot
import logging

from constants import Config, Inline, Replicas, UserStages
from locLibs import dbFunc, simpleClasses, botTools, simpleTools, reminders
from handlers.inlineCallBacks import addCbData, CbDataCC
from handlers.decorators import photoGrouping, processOnce
from handlers import threadWorker


def handleClientSide(msg: telebot.types.Message, task: dbFunc.Task):
    cbList = botTools.redirectMsg(msg, Replicas.CLENT_ANSWER)
    botTools.addComment(task.groupId, task.postId, cbList)
    botTools.forwardMessage(task.topicId, msg)


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
        pointInfo = dbFunc.getPointById(client.bind)

        dist = simpleTools.distToTimeSgm(pointInfo.workH)
        confirmText = Replicas.gen_confirm_text(pointInfo.city, pointInfo.name, dist)
        reply = self.bot.send_message(msg.chat.id, confirmText, reply_markup=inlineKeyboard, parse_mode='HTML')

        self.bot.register_next_step_handler_by_chat_id(
            reply.chat.id, self.answerInlineProducer, reply.id)  # reg waiting

        shrinkedMsg = simpleClasses.MsgContent(msg)
        addCbData((reply.chat.id, None), CbDataCC(client, pointInfo.name, shrinkedMsg))

    #   -client add message to existing task

    #   - entry point
    def handleClient(self, msg: telebot.types.Message):
        self.logger.debug('begin processing msg from client:' + str(msg.chat.id))
        taskInfo = dbFunc.getTaskByClientId(msg.from_user.id)
        if taskInfo is None:
            endTaskInfo = dbFunc.getClosedTaskByClientId(msg.from_user.id)
            if endTaskInfo is None:
                self.handleStartConversation(msg)
            else:  # * watcher reflection
                topicId = endTaskInfo.topicId
                botTools.forwardMessage(topicId, msg)
        else:
            handleClientSide(msg, taskInfo)
        self.logger.debug('end processing msg from client:' + str(msg.chat.id))


class ConsultantHandlers(simpleClasses.Handlers):
    def __init__(self):
        super().__init__()

    #   -redirect functions
    def redirectClientGen(self, msg: telebot.types.Message, client: dbFunc.Client, consultantName: str, topicId: int):
        msg: telebot.types.Message

        postMsg = msg.reply_to_message
        self.bot.send_message(client.id, Replicas.ON_CLIENT_REDIRECTION)

        answersList: list = dbFunc.getRegCities()
        answersList.append('/cancel')
        pointList = []
        newCity = ''
        while not pointList:
            cityIndex = yield from botTools.askToChoice(postMsg.chat.id, postMsg.id, None,
                                                        Replicas.SAY_ABOUT_CANCEL + '\n\n' + Replicas.ASK_ABOUT_REDIRECT_CITY,
                                                        answersList, False)
            if cityIndex == len(answersList) - 1:
                self.bot.send_message(client.id, Replicas.ON_REDIRECTTION_STOP)
                reply = self.bot.reply_to(postMsg, Replicas.ON_REDIRECTTION_STOP)
                yield reply, True

            newCity = answersList[cityIndex]

            pointList = dbFunc.getPointsByCity(newCity)
            if client.city == newCity:
                pointList.remove(next(i for i in pointList if i.id == postMsg.chat.id))

            if len(pointList) == 0:
                self.bot.reply_to(postMsg, Replicas.NO_SUITABLE_POINTS)

        answersList = list(map(lambda x: x.name, pointList))
        answersList.append('/cancel')

        pointIndx = yield from botTools.askToChoice(msg.chat.id, postMsg.id, None, Replicas.ASK_ABOUT_REDIRECT_POINT,
                                                    answersList, False)
        if pointIndx == len(answersList) - 1:
            self.bot.send_message(client.id, Replicas.ON_REDIRECTTION_STOP)
            reply = self.bot.reply_to(postMsg, Replicas.ON_REDIRECTTION_STOP)
            yield reply, True

        pointName = answersList[pointIndx]
        newBind = pointList[pointIndx]

        reply = self.bot.reply_to(postMsg, Replicas.ASK_ABOUT_REDIRECT_TEXT)
        msg = yield reply, False  # waiting for post msg

        if msg.text == '/cancel':
            self.bot.send_message(client.id, Replicas.ON_REDIRECTTION_STOP)
            reply = self.bot.reply_to(postMsg, Replicas.ON_REDIRECTTION_STOP)
            yield reply, True

        self.bot.send_message(client.id, Replicas.SUCSESS_REDIRECT)
        reply = self.bot.reply_to(postMsg, Replicas.SUCSESS_REDIRECT)

        dbFunc.changeClientBind(client.id, newCity, newBind.id)
        newClient = dbFunc.Client(client.id, client.name, newCity, newBind.id)
        newCh, newPostId = botTools.addNewTask(newClient, msg)

        dbFunc.changeTaskByPost(msg.chat.id, postMsg.id, newCh, newPostId)
        botTools.forwardRedir(topicId, consultantName, newCity, pointName, msg)
        reminders.delReminder(msg.chat.id, client.id)
        reminders.regReminder(newBind.id, client.id, client.name)
        yield reply, True

    def redirectClient(self, msg: telebot.types.Message, clientId: int, gen):
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

        clientState = self.bot.get_state(task.clientId)
        if clientState == UserStages.CLIENT_REDIR:
            return

        if msg.text == '/close':
            reminders.delReminder(replyChat, task.clientId)
            botTools.forwardMessage(task.topicId, msg)
            botTools.endFrorward(task.topicId, task.clientId)

            botTools.endTask(task.clientId)
        elif msg.text == '/ban':
            reminders.delReminder(replyChat, task.clientId)
            botTools.forwardMessage(task.topicId, msg)
            botTools.endFrorward(task.topicId, task.clientId)

            dbFunc.delTask(task.clientId)
            dbFunc.delClient(task.clientId)
            self.bot.send_message(task.clientId, Replicas.BANNED_TEXT)
            self.bot.reply_to(postMsg, 'banned')
            botTools.blockUser(task.clientId)
        elif msg.text == '/redirect':
            self.bot.set_state(task.clientId, UserStages.CLIENT_REDIR)

            client = dbFunc.getClientById(task.clientId)
            redirProc = self.redirectClientGen(msg, client, consultant.name, task.topicId)
            reply, stop = next(redirProc)
            if not stop:
                self.logger.debug('register redirect sess on: ' + str(replyChat) + '-' + str(replyId))
                self.bot.register_for_reply(postMsg, self.redirProducer, task.clientId, redirProc)
            else:
                self.bot.delete_state(task.clientId)
                self.bot.set_state(task.clientId, UserStages.CLIENT_IN_CONVERSATION)
        else:
            reminders.markReminder(replyChat, task.clientId)
            botTools.forwardMessage(task.topicId, msg)
            dbFunc.addNewActive(task.clientId, consultant.id)
            cbList = botTools.redirectMsg(msg, Replicas.CONSULTANT_ANSWER.format(consultant=consultant.name),
                                          parse_mode="HTML")
            for cb in cbList:
                cb(task.clientId, None)


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
