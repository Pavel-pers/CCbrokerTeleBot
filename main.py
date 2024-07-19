import telebot
import logging
from tokens import bot as botTokens
from locLibs import simpleClasses
from locLibs import dbFunc
import locLibs.botTools
import handlers

# setup logger
botLogger = logging.getLogger('bot')
handler = logging.FileHandler('log/.log', mode='a')
formatter = logging.Formatter('[%(asctime)s](%(name)s)%(levelname)s:%(message)s', '%H:%M:%S')
handler.setFormatter(formatter)
botLogger.addHandler(handler)
botLogger.setLevel(logging.DEBUG)

bot = simpleClasses.TeleBotBanF(botTokens.token, threaded=False, block_list=dbFunc.getBlockList())
locLibs.botTools.bot = bot
dbFunc.mainSqlLoop.start()

handlers.startListen(bot, botLogger)
# TODO realise delete group handler

try:
    bot.polling(none_stop=True)
except Exception as err:
    dbFunc.mainSqlLoop.killLoop()  # we crashed, shutdown loop
    raise err
