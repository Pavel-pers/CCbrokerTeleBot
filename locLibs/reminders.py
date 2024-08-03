import telebot
import logging
import threading
import time
from locLibs import dbFunc, simpleTools
from constants import Config


class ReminderList:
    def __init__(self, workH, backup):
        self.workH = workH
        self.cur_stage = dict()
        self.future_stage = dict()

        curTime = int(time.time())
        for cliendId, start, clientName in backup:
            if start + Config.REMINDER_DELAY < curTime:
                self.cur_stage[cliendId] = (start, clientName)
            else:
                self.future_stage[cliendId] = (start, clientName)

    def mark(self, clientId):
        inCurStage = self.cur_stage.pop(clientId, None)
        if inCurStage is not None:
            self.future_stage[clientId] = (int(time.time()), inCurStage[1])
        else:
            userName = self.future_stage[clientId][1]
            self.future_stage[clientId] = (int(time.time()), userName)
        return inCurStage is not None

    def addTask(self, clientId, clientName):
        self.future_stage[clientId] = (time.time(), clientName)

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
        self.future_stage = set()

    def genText(self, curTime) -> str:
        reminderText = ''
        for start, client in self.cur_stage.values():
            reminderText += f'\n{client} + waiting aproximatly {(curTime - start) / 3600:.1f}h'
        return reminderText


def worker(bot: telebot.TeleBot, reminders: dict):
    time.sleep(10 * 60)  # restore time after crash(for process messages, recieved on crash time)
    while True:
        time.sleep(Config.REMINDER_DELAY)
        curTime = time.time()

        for pointInfo in reminders.values():
            chatId, reminder = pointInfo
            if simpleTools.distToTimeSgm(reminder.workH) == 0:
                remText = reminder.genText(curTime)
                if remText:
                    bot.send_message(chatId, 'please, answer clients bellow' + remText)
            reminder.nextStage()


remindersDict = dict()


def regReminder(pointId, clientId, clientName):
    remindersDict[pointId].addTask(clientId, clientName)


def delReminder(pointId, clientId):
    remindersDict[pointId].delTask(clientId)


def markReminder(pointId, clientId):
    if remindersDict[pointId].mark(pointId, clientId):
        dbFunc.updActiveTime(clientId)


def startReminders(bot: telebot.TeleBot, taskList):
    row_info = dict()
    for row in taskList:
        pointId, clientId, activeTime = row[1], row[0], row[5]
        clientName = dbFunc.getClientById(clientId)
        if pointId not in row_info:
            workH = dbFunc.getPointById(pointId)[4]
            row_info[pointId] = (workH, [])
        row_info[pointId][1].append((pointId, clientId, activeTime))

    for point, workH, tasks in row_info.values():
        remindersDict[point] = ReminderList(workH, tasks)

    workerTh = threading.Thread(target=worker, args=(bot, remindersDict), daemon=True)
