from handlers import clientCommands
from handlers import regConsultant
from handlers import pointCommands
from handlers import inlineCallBacks
from handlers import taskSupport
from handlers.decorators import photoGrouping
from handlers import wacthers
import threading


def startListen(bot, botLogger):
    photoGrouping.startListen(bot, botLogger)  # must have first place
    inlineCallBacks.startListen(bot, botLogger)
    wacthers.startListening(bot, botLogger)
    clientCommands.startListen(bot, botLogger)
    pointCommands.startListen(bot, botLogger)
    regConsultant.startListen(bot, botLogger)
    taskSupport.startListenClient(bot, botLogger)
    taskSupport.startListenConsultant(bot, botLogger)
