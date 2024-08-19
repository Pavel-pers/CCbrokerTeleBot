import telebot
import logging
from handlers import threadWorker
from handlers.pointCommands import pendingPermitions
from locLibs import simpleClasses
from locLibs import dbFunc
from constants import Config, Replicas

FORUM_CHAT = Config.FORUM_CHAT


class WatchersHandler(simpleClasses.Handlers):
    def __init__(self):
        super().__init__()

    def showRating(self, msg: telebot.types.Message):
        pointDict = dict()

        def initPoint(row):
            chatId, city, name = row[:3]
            pointDict[chatId] = [[], 0, 0, (city, name)]

        def initConsultant(row):
            bind = row[5]
            if row[2] > 0:
                pointDict[bind][0].append((row[0], row[1], (row[3] / row[2], row[2]), row[4]))
            pointDict[bind][1] += row[2]
            pointDict[bind][2] += row[3]

        dbFunc.iterateTable([initPoint], 'Points').wait()
        dbFunc.iterateTable([initConsultant], 'Consultants').wait()

        groupedByCity = dict()

        pointList = []
        for pointId, pointInfo in pointDict.items():
            consultantList = pointInfo[0]
            pointCity, pointName = pointInfo[3]
            pointList.append(
                (pointCity + '_' + pointName, (pointInfo[2] / pointInfo[1] if pointInfo[1] else 0, pointInfo[1])))
            for consultant in consultantList:
                if pointCity not in groupedByCity:
                    groupedByCity[pointCity] = []
                groupedByCity[pointCity].append((consultant, pointName))

        consultantsLeaderBoard = Replicas.CONSULTANT_LEADERBOARD + '\n'
        for city, consultantsList in groupedByCity.items():
            consultantsLeaderBoard += Replicas.CITY_TEXT_LEADERBOARD.format(city)
            consultantsList = sorted(consultantsList, key=lambda x: x[0][1], reverse=True)
            for consultant, point in consultantsList:
                consultantId, name, rate, bonus = consultant
                text = Replicas.CONSULTANT_LEADER.format(tag=f'[@{name}](tg://user?id={consultantId})',
                                                         point_name=point, average=rate[0], count=rate[1], bonus=bonus)
                consultantsLeaderBoard += '\n' + text
            consultantsLeaderBoard += '\n\n'

        self.bot.send_message(msg.chat.id, consultantsLeaderBoard, parse_mode='Markdown')

        pointList = sorted(pointList, key=lambda x: x[1], reverse=True)
        pointLeaderBoard = Replicas.POINT_LEADERBOARD

        for pointName, rate in pointList:
            pointLeaderBoard += '\n' + Replicas.POINT_LEADER.format(name=pointName, rate=rate[0], count=rate[1])

        self.bot.send_message(msg.chat.id, pointLeaderBoard)

    def clearProgress(self, msg: telebot.types.Message):
        dbFunc.clearConsultantProgress()
        self.bot.send_message(msg.chat.id, Replicas.SUCSESS_CLEAR_CONSULTANT)

    def addPermission(self, msg: telebot.types.Message):
        if ' ' in msg.text:
            groupId = msg.text[msg.text.find(' ') + 1:]
            if groupId.isdigit():
                pendingPermitions.add(int(groupId))
                self.bot.send_message(msg.chat.id, Replicas.ON_PERMITION_ADDED)
                return
        self.bot.send_message(msg.chat.id, Replicas.INCORECT_FORMAT)


handlers = WatchersHandler()


def isFromGeneralTopic(msg: telebot.types.Message):
    return msg.chat.id == FORUM_CHAT and msg.message_thread_id is None


def startListening(bot: telebot.TeleBot, logger: logging.Logger):
    handlers.set_bot(bot)
    handlers.set_logger(logger)

    bot.message_handler(commands=['leaderboard', 'leaders'], func=isFromGeneralTopic)(handlers.showRating)
    bot.message_handler(commands=['clear_progress'], func=isFromGeneralTopic)(handlers.clearProgress)
    bot.message_handler(commands=['add_point'], func=isFromGeneralTopic)(handlers.addPermission)

    @bot.message_handler(content_types=Config.ALLOWED_CONTENT, func=lambda msg: msg.chat.id == FORUM_CHAT)
    def unexpectedHandler(msg: telebot.types.Message):
        pass

    bot.my_chat_member_handler()
