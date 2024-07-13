import csv
import sqlite3

import threading
import queue
import logging

import time

dbConn = sqlite3.connect('data/database.db', check_same_thread=False)
if __name__ == "__main__":
    dbCurr = dbConn.cursor()
    dbCurr.execute("""CREATE TABLE IF NOT EXISTS Tasks(
        clientId INTEGER PRIMARY KEY,
        groupId INTEGER,
        postId INTEGER,
        birthTime INTEGER
    );
    CREATE UNIQUE INDEX IF NOT EXISTS task_client_id ON Tasks (clientId)""")
    dbConn.commit()

    dbCurr.execute("""CREATE TABLE IF NOT EXISTS Clients(
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        city TEXT NOT NULL,
        bind INTEGER
    );
    CREATE UNIQUE INDEX IF NOT EXISTS client_id ON Clients(id)""")
    dbConn.commit()

    dbCurr.execute("""CREATE TABLE IF NOT EXISTS Consultats(
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        rate INTEGER,
        answers INTEGER,
        bonus INTEGER
    );
    CREATE UNIQUE INDEX IF NOT EXISTS consultats_id ON Consultats(id)""")
    dbConn.commit()

    dbCurr.execute("""CREATE TABLE IF NOT EXISTS Points(
        id INTEGER PRIMARY KEY,
        city TEXT NOT NULL,
        name TEXT NOT NULL,
        workH TEXT NOT NULL
    );
    CREATE UNIQUE INDEX IF NOT EXISTS point_id ON Points(id)""")
    dbConn.commit()


# -csv functions
def getCityList():
    cities = []
    with open('data/cities.csv', 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            cities.append(row[0])
    return cities


# -sqlite functions
def sqlWorker(workQueue: queue.Queue, finishEvent: threading.Event):
    dbCur = dbConn.cursor()

    while not workQueue.empty() or not finishEvent.is_set():
        try:
            commandInfo, callback = workQueue.get(timeout=5)
        except queue.Empty:
            continue

        dbCur.execute(*commandInfo)
        callback(dbCur)


class SqlRequest:
    def __init__(self, commInfo, onProcesed):  # runs commInfo into cursor execute, takes result from onProcesed func
        self.processed = threading.Event()
        self.onProcesed = onProcesed
        self.result = None

    def wait(self):
        self.processed.wait()
        return self.result

    def callback(self, dbCur):
        self.result = self.onProcesed(dbCur)
        self.processed.set()


class SqlLoop:
    def __init__(self, logger: logging.Logger, maxsize=20):
        self.finishEv = threading.Event()

        self.workQ = queue.Queue(maxsize)
        self.workTh = threading.Thread(target=sqlWorker, args=(self.workQ, self.finishEv))
        self.workTh.start()

        self.logger = logger
        self.logger.info('loop started')

    def addTask(self, commInfo, onProcesed) -> SqlRequest:  # returns request class
        request = SqlRequest(commInfo, onProcesed)
        try:
            self.workQ.put_nowait(request)
        except queue.Full:
            self.logger.warning('queue full')
            self.workQ.put(request)
        return request

    def killLoop(self, blocking=True):
        self.finishEv.set()
        if blocking:
            self.workTh.join()


# point requests
def addNewPoint(loop: SqlLoop, groupId, city, name, workHours):
    # TODO add validator
    command = (('INSERT INTO Points (id, city, name, workH) VALUES (?, ?, ?, ?)',
                (groupId, city, name, workHours)))
    loop.addTask(command, lambda dbCur: dbConn.commit())


def getPointsByCity(loop: SqlLoop, city):
    command = ('SELECT * FROM Points WHERE city=?', (city,))
    task = loop.addTask(command, lambda dbCur: dbCur.fetchall())
    return task.wait()


def getPointById(loop: SqlLoop, chatId):
    command = ('SELECT * FROM Points WHERE id=?', (chatId,))
    task = loop.addTask(command, lambda dbCur: dbCur.fetchone())
    return task.wait()


# client requests
def addNewClient(loop: SqlLoop, chatId, name, city, bindId):
    def onProc(dbCur):
        if dbCur.fetchone() is None:  # create new client
            addTask = ('INSERT INTO Clients (id, name, city, bind) VALUES (?, ?, ?, ?)', (chatId, name, city, bindId))
            loop.addTask(addTask, lambda dbCur1: dbConn.commit())
        else:  # upadate info
            updTask = ('UPDATE Clients SET name = ?, city = ?, bind = ? WHERE id = ?', (name, city, bindId, chatId))
            loop.addTask(updTask, lambda dbCur1: dbConn.commit())

    checkTask = ('SELECT id FROM Clients WHERE id = ?', (chatId,))
    loop.addTask(checkTask, onProc)


def getClientById(loop: SqlLoop, userId):
    command = ('SELECT * FROM Clients WHERE id=?', (userId,))
    task = loop.addTask(command, lambda dbCur: dbCur.fetchone())
    return task.wait()


# consultant requests
def addNewConsultant(loop: SqlLoop, userId, name):
    def onProc(dbCur):
        if dbCur.fetchone() is None:  # create new Consultant
            addTask = ('INSERT INTO Consultants (id, name) VALUES (?, ?)', (userId, name))
            loop.addTask(addTask, lambda dbCur1: dbConn.commit())
        else:
            updTask = ('UPDATE Consultants SET name = ? WHERE id = ?', (name, userId))
            loop.addTask(updTask, lambda dbCur1: dbConn.commit())

    checkTask = ('SELECT id FROM Consultants WHERE id = ?', (userId,))
    loop.addTask(checkTask, onProc)


def getConsultantById(loop: SqlLoop, userId):
    command = ('SELECT * FROM Consultants WHERE id=?', (userId,))
    task = loop.addTask(command, lambda dbCur: dbCur.fetchone())
    return task.wait()


# task requests
def addNewTask(loop: SqlLoop, clientId, groupId, postId):
    birthTime = time.time() // 60  # ? save time info in minutes
    command = ('INSERT INTO Tasks (clientId, groupId, postId, birthTime) VALUES (?, ?, ?, ?)',
               (clientId, groupId, postId, birthTime))
    loop.addTask(command, lambda dbCur: dbConn.commit())


def getTaskByClientId(loop: SqlLoop, clientId):
    command = ('SELECT * FROM Tasks WHERE clientId=?', (clientId,))
    task = loop.addTask(command, lambda dbCur: dbCur.fetchone())
    return task.wait()


def changeTaskPost(loop: SqlLoop, prevGroup, prevId, newGroup, newId):
    command = ('UPDATE Tasks SET groupId = ?, postId = ? WHERE groupId=? AND postId=?',
               (newGroup, newId, prevGroup, prevId))

    loop.addTask(command, lambda dbCur: dbConn.commit())


def getTaskByPost(loop: SqlLoop, groupId, postId):
    command = ('SELECT * FROM Tasks WHERE groupId=? AND postId=?', (groupId, postId))
    task = loop.addTask(command, lambda dbCur: dbCur.fetchone())
    return task.wait()


def delTask(loop: SqlLoop, clientId):
    command = ('DELETE FROM Tasks WHERE clientId=?', (clientId,))
    task = loop.addTask(command, lambda dbCur: dbConn.commit())
