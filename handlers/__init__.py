from handlers import regClient
from handlers import regConsultant
from handlers import regPoint
from handlers import inlineCallBacks
from handlers import taskSupport
import threading


def startListen(bot, botLogger):
    inlineCallBacks.startListen(bot, botLogger)
    regClient.startListen(bot, botLogger)
    regConsultant.startListen(bot, botLogger)
    regPoint.startListen(bot, botLogger)
    taskSupport.startListenClient(bot, botLogger)
    taskSupport.startListenConsultant(bot, botLogger)
