from locLibs import botTools
from locLibs import dbFunc
from locLibs import reminders
from locLibs import simpleClasses
from locLibs import simpleTools
from locLibs import dataCaching


def init(bot, logger):
    botTools.bot = bot
    botTools.logger = logger
