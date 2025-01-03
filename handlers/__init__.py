from handlers import clientCommands
from handlers import consultantCommands
from handlers import pointCommands
from handlers import inlineCallBacks
from handlers import taskSupport
from handlers.decorators import photoGrouping
from handlers import wacthers


def startListen(bot, botLogger):
    photoGrouping.startListen(bot, botLogger)  # !must have first place
    inlineCallBacks.startListen(bot, botLogger)  # * backend
    wacthers.startListening(bot, botLogger)  # !must be first before backend because of watcher reflection
    clientCommands.startListen(bot, botLogger)
    pointCommands.startListen(bot, botLogger)
    consultantCommands.startListen(bot, botLogger)  # * commands handlers
    taskSupport.startListenClient(bot, botLogger)
    taskSupport.startListenConsultant(bot, botLogger)  # * task handlers
