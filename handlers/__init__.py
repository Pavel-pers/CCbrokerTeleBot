from handlers import regClient
from handlers import regConsultant
from handlers import regPoint
from handlers import inlineCallBacks
from handlers import taskSupport
from handlers.decorators import photoGrouping
from handlers import wacthers
import threading


def startListen(bot, botLogger):
    photoGrouping.startListen(bot, botLogger)  # must have first place
    inlineCallBacks.startListen(bot, botLogger)
    regClient.startListen(bot, botLogger)
    regConsultant.startListen(bot, botLogger)
    regPoint.startListen(bot, botLogger)
    taskSupport.startListenClient(bot, botLogger)
    taskSupport.startListenConsultant(bot, botLogger)
    wacthers.startListening(bot, botLogger)
