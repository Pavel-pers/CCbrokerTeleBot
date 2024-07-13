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
        callback(dbCur, dbConn)


class SqlRequest:
    def __init__(self, commInfo, onProcesed):  # runs commInfo into cursor execute, takes result from onProcesed func
        self.processed = threading.Event()
        self.onProcesed = onProcesed
        self.result = None

    def wait(self):
        self.processed.wait()
        return self.result

    def callback(self, dbCur, dbConn):
        self.result = self.onProcesed(dbCur, dbConn)
        self.processed.set()


class SqlLoop:
    def __init__(self, logger: logging.Logger, maxsize=20):
        self.finishEv = threading.Event()

        self.workQ = queue.Queue(maxsize)
        self.workTh = threading.Thread(target=sqlWorker, args=(self.workQ, self.finishEv))
        self.workTh.start()

        self.logger = logger
        self.logger.info('loop started')

    def addTask(self, commInfo, onProcesed):  # returns request class
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
def addNewPoint(groupId, city, name, workHours):
    # TODO add validator
    dbCur.execute('INSERT INTO Points (id, city, name, workH) VALUES (?, ?, ?, ?)',
                  (groupId, city, name, workHours))
    dbConn.commit()


def getPointsByCity(city):
    dbCur.execute('SELECT * FROM Points WHERE city=?', (city,))
    return dbCur.fetchall()


def getPointById(chatId):
    dbCur.execute('SELECT * FROM Points WHERE id=?', (chatId,))
    return dbCur.fetchone()


# client requests
def addNewClient(chatId, name, city, bindId):
    dbCur.execute('SELECT id FROM Clients WHERE id = ?', (chatId,))
    if dbCur.fetchone() is None:  # create new client
        dbCur.execute('INSERT INTO Clients (id, name, city, bind) VALUES (?, ?, ?, ?)', (chatId, name, city, bindId))
    else:  # upadate info
        dbCur.execute('UPDATE Clients SET name = ?, city = ?, bind = ? WHERE id = ?', (name, city, bindId, chatId))
    dbConn.commit()


def getClientById(userId):
    dbCur.execute('SELECT * FROM Clients WHERE id=?', (userId,))
    return dbCur.fetchone()


# consultant requests
def addNewConsultant(userId, name):
    dbCur.execute('SELECT id FROM Consultants WHERE id = ?', (userId,))
    if dbCur.fetchone() is None:  # create new Consultant
        dbCur.execute('INSERT INTO Consultants (id, name) VALUES (?, ?)', (userId, name))
    else:
        dbCur.execute('UPDATE Consultants SET name = ? WHERE id = ?', (name, userId))
    dbConn.commit()


def getConsultantById(userId):
    dbCur.execute('SELECT * FROM Consultants WHERE id=?', (userId,))
    return dbCur.fetchone()


# task requests
def addNewTask(clientId, groupId, postId):
    birthTime = time.time() // 60  # ? save time info in minutes
    dbCur.execute('INSERT INTO Tasks (clientId, groupId, postId, birthTime) VALUES (?, ?, ?, ?)',
                  (clientId, groupId, postId, birthTime))
    dbConn.commit()


def getTaskByClientId(clientId):
    dbCur.execute('SELECT * FROM Tasks WHERE clientId=?', (clientId,))
    return dbCur.fetchone()


def changeTaskPost(prevGroup, prevId, newGroup, newId):
    dbCur.execute('UPDATE Tasks SET groupId = ?, postId = ? WHERE groupId=? AND postId=?',
                  (newGroup, newId, prevGroup, prevId))
    dbConn.commit()


def getTaskByPost(groupId, postId):
    dbCur.execute('SELECT * FROM Tasks WHERE groupId=? AND postId=?', (groupId, postId))
    return dbCur.fetchone()


def delTask(clientId):
    dbCur.execute('DELETE FROM Tasks WHERE clientId=?', (clientId,))
    dbConn.commit()
