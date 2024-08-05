import telebot
import logging
import threading
import time

import constants
from locLibs import dbFunc, simpleTools
from constants import Config


class ReminderList:
    def __init__(self, workH):
        self.workH = workH
        self.cur_stage = dict()
        self.future_stage = dict()

    def mark(self, clientId):  # returns True if task in current stage
        inCurStage = self.cur_stage.pop(clientId, None)
        if inCurStage is not None:
            self.future_stage[clientId] = (int(time.time()), inCurStage[1])
        else:
            userName = self.future_stage[clientId][1]
            self.future_stage[clientId] = (int(time.time()), userName)
        return inCurStage is not None

    def addTask(self, clientId, clientName, mdfTime=None):
        curTime = int(time.time())
        if mdfTime is not None:
            if Config.REMINDER_DELAY + mdfTime < curTime:
                self.cur_stage[clientId] = (mdfTime, clientName)
            else:
                self.future_stage[clientId] = (mdfTime, clientName)
        else:
            self.future_stage[clientId] = (curTime, clientName)

    def delTask(self, clientId):
        curStage = self.cur_stage.pop(clientId, None)
        if curStage is None:
            self.future_stage.pop(clientId)

    def nextStage(self):
        if len(self.cur_stage) < len(self.future_stage):
            self.future_stage.update(self.cur_stage)
            self.cur_stage = self.future_stage
        else:
            self.cur_stage.update(self.future_stage)
        self.future_stage = dict()

    def genText(self, curTime) -> str:
        reminderText = ''
        for start, client in self.cur_stage.values():
            reminderText += f'\n{client} + waiting aproximatly {(curTime - start) / 3600:.1f}h'
        return reminderText


def worker(bot: telebot.TeleBot, logger: logging.Logger, reminders: dict):
    time.sleep(10 * 60)  # restore time after crash(for process messages, recieved on crash time)
    while True:
        time.sleep(Config.REMINDER_DELAY)
        curTime = time.time()
        logger.debug('--new reminder iter--')
        with remindersLock:
            for pointInfo in reminders.items():
                chatId, reminder = pointInfo
                logger.debug('processing:' + str(chatId) + ' ' + reminder.workH)
                if simpleTools.distToTimeSgm(reminder.workH) == 0:
                    logger.debug('check stages:' + str(chatId))
                    logger.debug('about stages ' + str(chatId) + 'cur:' + str(reminder.cur_stage) + 'fut:' + str(
                        reminder.future_stage))
                    remText = reminder.genText(curTime)
                    if remText:
                        bot.send_message(chatId, 'please, answer clients bellow' + remText)

                logger.debug('finish with:' + str(chatId))
                reminder.nextStage()


remindersLock = threading.Lock()
remindersDict: dict[int, ReminderList] = dict()


def addPoint(pointId, pointHours):
    with remindersLock:
        remindersDict[pointId] = ReminderList(pointHours)


def changePoint(pointId, pointHours):
    with remindersLock:
        remindersDict[pointId].workH = pointHours


def regReminder(pointId, clientId, clientName, mdfTime=None):
    with remindersLock:
        remindersDict[pointId].addTask(clientId, clientName, mdfTime)


def delReminder(pointId, clientId):
    with remindersLock:
        remindersDict[pointId].delTask(clientId)


def markReminder(pointId, clientId):
    with remindersLock:
        if remindersDict[pointId].mark(clientId):
            dbFunc.updActiveTime(clientId)


def startReminders(bot: telebot.TeleBot, logger: logging.Logger):
    dbFunc.initTable([lambda row: addPoint(row[0], row[3])], 'Points')
    taskList = dbFunc.getAllData('Tasks', ('groupId', 'clientId', 'lastActiveTime'))
    for pointId, clientId, startTime in taskList:
        clientName = dbFunc.getClientById(clientId)[1]
        regReminder(pointId, clientId, clientName, startTime)

    workerTh = threading.Thread(target=worker, args=(bot, logger, remindersDict), daemon=True)
    workerTh.start()
    return workerTh
