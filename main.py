import logging

import telebot
from tokens import bot as botTokens

from locLibs import dbFunc

# uesr stages
CLIENT_REDIR = 1
CLIENT_REG = 2
# setup logger
botLogger = logging.getLogger('bot')
handler = logging.FileHandler('log/bot.log', mode='w')
formatter = logging.Formatter('[%(asctime)s](%(name)s)%(levelname)s:%(message)s', '%H:%M:%S')
handler.setFormatter(formatter)
botLogger.addHandler(handler)
botLogger.setLevel(logging.DEBUG)

bot = telebot.TeleBot(botTokens.token)  # auth bot, turn on sql loop
dbFunc.mainSqlLoop.start()


def isMsgFromPoint(msg: telebot.types.Message):
    return msg.chat.type in ['supergroup', 'channel'] and dbFunc.getPointById(
        msg.chat.id) is not None or dbFunc.getPointById(
        bot.get_chat(msg.chat.id).linked_chat_id) is not None


def getRelpyFromAdmin(reply, stopReg):
    msg = yield reply, stopReg
    while bot.get_chat_member(msg.chat.id, msg.from_user.id).status not in ['administrator', 'creator']:
        botLogger.debug(bot.get_chat_member(msg.chat.id, msg.from_user.id))
        reply = bot.send_message(msg.chat.id, 'you are not admin..')
        msg = yield reply, False
    return msg


#  registration functions
#  -reg point functions
def regPointGen(msg: telebot.types.Message):
    cityKeyboard = telebot.types.ReplyKeyboardMarkup()
    cityList = dbFunc.getCityList()

    for city in cityList:
        cityKeyboard.add(city)

    reply = bot.send_message(msg.chat.id, 'welcome group, ask about city', reply_markup=cityKeyboard)
    msg: telebot.types.Message = yield from getRelpyFromAdmin(reply, False)
    pointCity = msg.text

    while pointCity not in cityList:
        reply = bot.send_message(msg.chat.id, 'incorrect city', reply_markup=cityKeyboard)
        msg = yield from getRelpyFromAdmin(reply, False)
        pointCity = msg.text

    reply = bot.send_message(msg.chat.id, 'ask about name say about /rename',
                             reply_markup=telebot.types.ReplyKeyboardRemove())
    msg = yield from getRelpyFromAdmin(reply, False)
    pointName = msg.text

    # TODO ask about work hours

    botLogger.debug('saving point:' + str((msg.chat.id, pointName, pointCity)))
    dbFunc.addNewPoint(msg.chat.id, pointCity, pointName, '')
    reply = bot.send_message(msg.chat.id, 'data saved')
    yield reply, True


def regPoint(msg: telebot.types.Message, gen):
    botLogger.debug('next reg iteration')
    reply, stopReg = gen.send(msg)
    if not stopReg:
        bot.register_next_step_handler(reply, regPoint, gen)


@bot.message_handler(commands=['start'], func=lambda message: message.chat.type == 'supergroup')
def welcomePoint(msg: telebot.types.Message):
    # TODO validate group
    botLogger.debug('welcome point')
    botLogger.debug('got msg from:' + bot.get_chat_member(msg.chat.id, msg.from_user.id).status)
    regGenerator = regPointGen(msg)
    reply, stopReg = next(regGenerator)
    if not stopReg:
        bot.register_next_step_handler(reply, regPoint, regGenerator)


# -reg client functions
def regClientGen(msg: telebot.types.Message, client=(None, None, None)):
    if client[0] is None:
        reply = bot.send_message(msg.chat.id, 'ask about his name')
        msg: telebot.types.Message = yield reply, False
        client = (msg.text, client[1], client[2])

    pointList = []
    if client[1] is None:
        cityKeyboard = telebot.types.ReplyKeyboardMarkup()  # prepare keybaard
        cityList = dbFunc.getRegCityList()
        for city in cityList:
            cityKeyboard.add(city)

        reply = bot.send_message(msg.chat.id, 'ask about city, say about /rename', reply_markup=cityKeyboard)
        msg = yield reply, False
        while msg.text not in cityList:  # wait for correct city
            reply = bot.send_message(msg.chat.id, 'incorrect city', reply_markup=cityKeyboard)
            msg = yield reply, False

        client = (client[0], msg.text, client[2])
    clientCity = client[1]

    if client[2] is None:
        pointKeyboard = telebot.types.ReplyKeyboardMarkup()  # prepare keyboard
        pointList = dbFunc.getPointsByCity(clientCity)
        for point in pointList:
            pointKeyboard.add(point[2])

        reply = bot.send_message(msg.chat.id, 'ask about point, say about /change_point', reply_markup=pointKeyboard)
        msg = yield reply, False
        while msg.text not in map(lambda el: el[2], pointList):  # wait for correct point
            reply = bot.send_message(msg.chat.id, 'incorrect point', reply_markup=pointKeyboard)
            msg = yield reply, False

        # find point by point name
        clientBindId = next(pTuple for pTuple in pointList if pTuple[2] == msg.text and pTuple[1] == clientCity)[0]
        client = (client[0], client[1], clientBindId)

    botLogger.debug('saving client:' + str((msg.from_user.id, client)))
    dbFunc.addNewClient(msg.from_user.id, *client)

    reply = bot.send_message(msg.chat.id, 'data saved, say about /change_point',
                             reply_markup=telebot.types.ReplyKeyboardRemove())
    yield reply, True


def regClient(msg: telebot.types.Message, gen):
    botLogger.debug('next reg iteration')
    reply, stopReg = gen.send(msg)
    if not stopReg:
        bot.register_next_step_handler(reply, regClient, gen)


@bot.message_handler(commands=['start'], func=lambda message: message.chat.type == 'private')
def welcomeClient(msg: telebot.types.Message):
    botLogger.debug('welcome user')
    regProc = regClientGen(msg)
    reply, stopReg = next(regProc)
    if not stopReg:
        bot.register_next_step_handler(reply, regClient, regProc)


# -reg consultant
@bot.message_handler(commands=['set_name', 'rename'], func=lambda msg: dbFunc.getPointById(msg.chat.id) is not None)
def setNameConsultant(msg: telebot.types.Message):
    name = msg.text
    name = name[name.find(' ') + 1:]
    botLogger.debug('set name for user:' + str(msg.from_user.id) + ' on ' + name)
    dbFunc.addNewConsultant(msg.from_user.id, name)


# -edit functions
#   -client side
#       -change point
@bot.message_handler(commands=['change_point'], func=lambda message: message.chat.type == 'private')
def changeClientPoint(msg: telebot.types.Message):
    client = dbFunc.getClientById(msg.chat.id)
    if client is None:
        bot.send_message(msg.chat.id, 'please enter /start for register')
        return

    replaceProc = regClientGen(msg, (client[1], None, None))
    reply, stopReg = next(replaceProc)
    if not stopReg:
        bot.register_next_step_handler(reply, regClient, replaceProc)


#       -change name
@bot.message_handler(commands=['set_name', 'rename'], func=lambda message: message.chat.type == 'private')
def changeClientName(msg: telebot.types.Message):
    client = dbFunc.getClientById(msg.chat.id)
    if client is None:
        bot.send_message(msg.chat.id, 'please enter /start for register')
        return

    renameProc = regClientGen(msg, (None, client[2], client[3]))
    reply, stopReg = next(renameProc)
    if not stopReg:
        bot.register_next_step_handler(reply, regClient, renameProc)


# TODO realise delete group handler

# functions for communication
#   -handle repeat message from telegram
@bot.message_handler(func=lambda message: message.from_user.id == 777000 and isMsgFromPoint(message))
def catchChannelMsg(msg: telebot.types.Message):
    originGr = msg.forward_origin.chat.id
    originId = msg.forward_origin.message_id
    curGr = msg.chat.id
    curId = msg.message_id
    botLogger.debug(f'catched telegram msg: {repr(msg.text)}. {originGr}, {originId}, changing on: {curGr}, {curId}')
    dbFunc.changeTaskPost(originGr, originId, curGr, curId)


# task functions
#   - post message and save in DB
def addNewTask(client, postText):
    clientId, clientName, clientCity, clientBind = client
    clientChannel = bot.get_chat(clientBind).linked_chat_id
    botLogger.debug('begin conversation between ' + str(clientId) + ', ' + str(clientBind))
    taskPost = bot.send_message(clientChannel, 'name:' + clientName + ', city:' + clientCity + '\n' + postText)
    dbFunc.addNewTask(clientId, taskPost.chat.id, taskPost.id)


#   - delete data in DB and ask client
def endTask(clientId):
    # TODO ask for rate
    bot.send_message(clientId, 'the end of conversation')
    dbFunc.delTask(clientId)


#   -handle client side
#       -client starts a conversation
def handleStartConversation(msg: telebot.types.Message):
    # TODO confirm start conversation
    client = dbFunc.getClientById(msg.from_user.id)
    if client is None:  # client has skiped the registration
        bot.send_message(msg.chat.id, 'please enter /start for register')
        return

    addNewTask(client, msg.text)


#       -client add message to existing task
def handleClientSide(msg: telebot.types.Message, taskInfo):
    client, group, postId = taskInfo[:3]  # skips birth info

    twinChat = telebot.types.Chat(group, 'supergroup')
    twinMsg = type('twinMsg', (object,), {'chat': twinChat, 'message_id': postId})
    bot.reply_to(twinMsg, msg.text)


#       -handle new message from client
@bot.message_handler(func=lambda message: message.chat.type == 'private')
def handleClient(msg: telebot.types.Message):
    taskInfo = dbFunc.getTaskByClientId(msg.from_user.id)
    if taskInfo is None:
        handleStartConversation(msg)
    else:
        handleClientSide(msg, taskInfo)


#   -handle consultant side
#       -post checker
def isPostReply(msg: telebot.types.Message):
    return msg.reply_to_message is not None and msg.reply_to_message.from_user.id == 777000 and isMsgFromPoint(msg)


#       -handle redirect command
def redirectClientGen(msg: telebot.types.Message, client):
    postMsg = msg.reply_to_message
    clientId, clientName, clientCity, clientBind = client
    bot.send_message(clientId, 'you gonna redirect')

    cityList = dbFunc.getRegCityList()
    reply = bot.reply_to(postMsg, 'say about /cancel, ask about city\ncities:\n' + '\n'.join(cityList))

    pointList = []
    newCity = ''
    while len(pointList) == 0:  # ! not vertified
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
            bot.send_message(postMsg, 'there are no suitable points')

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

    postText = msg.text
    bot.send_message(clientId, 'redirect successfully')
    reply = bot.reply_to(postMsg, 'redirect successfully')

    dbFunc.delTask(clientId)
    dbFunc.changeClientBind(clientId, newCity, newPoint)
    newClient = (client[0], client[1], newCity, newPoint)
    addNewTask(newClient, postText)
    yield reply, True


def redirectClient(msg: telebot.types.Message, clientId, gen):
    post = msg.reply_to_message
    reply, stop = gen.send(msg)
    if not stop:
        bot.register_for_reply(post, redirectClient, clientId, gen)
    else:
        bot.delete_state(clientId)


#       -handler consultant messages, ignore redireced sessions
@bot.message_handler(func=isPostReply)
def handleConsultant(msg: telebot.types.Message):
    consultant = dbFunc.getConsultantById(msg.from_user.id)
    if consultant is None:  # consultant has skiped the registration
        bot.send_message(msg.chat.id, 'please enter /set_name <NAME> for register')
        return

    postMsg = msg.reply_to_message
    replyChat = postMsg.chat.id
    replyId = postMsg.message_id
    task = dbFunc.getTaskByPost(replyChat, replyId)
    if task is None:
        bot.send_message(msg.chat.id, 'this post is not supported')
        return

    botLogger.debug('processing comment:' + str(replyChat) + '-' + str(replyId))
    clientId = task[0]
    clientState = bot.get_state(clientId)
    if clientState == CLIENT_REDIR:
        return

    if msg.text == '/close':
        endTask(clientId)
    elif msg.text == '/redirect':
        bot.set_state(clientId, CLIENT_REDIR)

        client = dbFunc.getClientById(clientId)
        redirProc = redirectClientGen(msg, client)
        reply, stop = next(redirProc)
        if not stop:
            botLogger.debug('register redirect sess on: ' + str(replyChat) + '-' + str(replyId))
            bot.register_for_reply(postMsg, redirectClient, clientId, redirProc)
    else:
        signedMsg = 'consultant name: ' + consultant[1] + '\n' + msg.text
        bot.send_message(clientId, signedMsg)


try:
    bot.polling(none_stop=True)
except Exception as err:
    dbFunc.mainSqlLoop.killLoop()  # we crashed, shutdown loop
    raise err
