import telebot
import logging
from tokens import telegramBot as botTokens
import locLibs
import handlers

# setup logger
botLogger = logging.getLogger('bot')
handler = logging.FileHandler('log/.log', mode='a')
formatter = logging.Formatter('[%(asctime)s](%(name)s)%(levelname)s:%(message)s', '%H:%M:%S')
handler.setFormatter(formatter)
botLogger.addHandler(handler)
botLogger.setLevel(logging.DEBUG)

# setup bot and reg it
bot = locLibs.simpleClasses.TeleBotBanF(botTokens.token, threaded=False, block_list=locLibs.dbFunc.getBlockList())
locLibs.init(bot, botLogger)
locLibs.dbFunc.mainSqlLoop.start()
locLibs.botTools.backupStages()
locLibs.reminders.startReminders(bot, botLogger)

handlers.startListen(bot, botLogger)
# TODO realise delete group handler

try:
    bot.polling(none_stop=True)
except Exception as err:
    locLibs.dbFunc.mainSqlLoop.killLoop()  # we crashed, shutdown the loop
    raise err
