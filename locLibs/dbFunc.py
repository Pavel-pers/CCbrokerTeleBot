import csv
import sqlite3

import threading
import queue
import logging

import time

dbLogger = logging.getLogger('DB_main')
handler = logging.FileHandler('log/db.log', mode='w')
formatter = logging.Formatter('[%(asctime)s](%(name)s)%(levelname)s:%(message)s', '%H:%M:%S')
handler.setFormatter(formatter)
dbLogger.addHandler(handler)
dbLogger.setLevel(logging.DEBUG)

dbConn = sqlite3.connect('data/database.db', check_same_thread=False)
if __name__ == "__main__":
    print('create table')
    dbCurr = dbConn.cursor()
    dbCurr.execute("""CREATE TABLE IF NOT EXISTS Tasks(
        clientId INTEGER PRIMARY KEY,
        groupId INTEGER,
        postId INTEGER,
        birthTime INTEGER
    )""")
    dbConn.commit()

    dbCurr.execute("""CREATE TABLE IF NOT EXISTS Clients(
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        city TEXT NOT NULL,
        bind INTEGER
    );""")
    dbConn.commit()

    dbCurr.execute("""CREATE TABLE IF NOT EXISTS Consultants(
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        rate INTEGER DEFAULT 0,
        answers INTEGER DEFAULT 0,
        bonus INTEGER DEFAULT 0
    );""")
    dbConn.commit()

    dbCurr.execute("""CREATE TABLE IF NOT EXISTS Points(
        id INTEGER PRIMARY KEY,
        city TEXT NOT NULL,
        name TEXT NOT NULL,
        workH TEXT DEFAULT NULL 
    );""")
    dbConn.commit()


# -csv functions
def getCityList():
    cities = []
    with open('data/cities.csv', 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            cities.append(row[0])
    return cities


csvCityLock = threading.Lock()


def getRegCityList():
    cities = []
    with open('data/regCities.csv', 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            cities.append(row[0])
    return cities


def addRegCity(city):
    dbLogger.debug('add ' + city)
    cities = getRegCityList()
    with csvCityLock:
        if city not in cities:
            with open('data/regCities.csv', 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([city, 1])
        else:
            citiesC = []
            with open('data/regCities.csv', 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    row[1] = int(row[1])
                    if row[0] == city:
                        row[1] += 1
                    citiesC.append(row)
            with open('data/regCities.csv', 'w', newline='') as f:
                writer = csv.writer(f)
                for row in citiesC:
                    writer.writerow(row)


def delRegCity(city):  # TODO validate func
    dbLogger.debug('delete ' + city)
    with csvCityLock:
        citiesC = []
        with open('data/regCities.csv', 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                row[1] = int(row[1])
                if row[0] == city:
                    row[1] -= 1
                if row[1] > 0:
                    citiesC.append(row)
        with open('data/regCities.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            for row in citiesC:
                writer.writerow(row)


# -sqlite functions
def sqlWorker(workQueue: queue.Queue, finishEvent: threading.Event):
    dbCur = dbConn.cursor()

    while not workQueue.empty() or not finishEvent.is_set():
        try:
            request: SqlRequest = workQueue.get(timeout=5)
        except queue.Empty:
            continue

        dbCur.execute(*request.command)  # unpack tuple to str and varible tuple
        request.callback(dbCur)


class SqlRequest:
    def __init__(self, commInfo, onProcesed):  # runs commInfo into cursor execute, takes result from onProcesed func
        self.command = commInfo
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
        self.logger = logger

    def start(self):
        self.workTh.start()
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
        self.logger.info('stopping loop')
        self.finishEv.set()
        if blocking:
            self.workTh.join()
            self.logger.info('stopped loop')


mainSqlLoop = SqlLoop(dbLogger)


# point requests
def addNewPoint(groupId, city, name, workHours, loop: SqlLoop = mainSqlLoop):
    # TODO add validator
    def onProc(dbCur: sqlite3.Cursor):
        fetch = dbCur.fetchone()
        if fetch is None:
            addRegCity(city)
            addTask = (
                'INSERT INTO Points (id, city, name, workH) VALUES (?, ?, ?, ?)', (groupId, city, name, workHours))
            loop.addTask(addTask, lambda dbCur1: dbConn.commit())
        else:
            prevCity = fetch[1]
            delRegCity(prevCity)
            addRegCity(city)
            updTask = (
                'UPDATE Points SET city = ?, name = ?, workH = ? WHERE id = ?', (city, name, workHours, groupId)
            )
            loop.addTask(updTask, lambda dbCur1: dbConn.commit())

    checkTask = ('SELECT * FROM Points WHERE id = ?', (groupId,))
    loop.addTask(checkTask, onProc)


def getPointsByCity(city, loop: SqlLoop = mainSqlLoop):
    command = ('SELECT * FROM Points WHERE city=?', (city,))
    task = loop.addTask(command, lambda dbCur: dbCur.fetchall())
    return task.wait()


def getPointById(chatId, loop: SqlLoop = mainSqlLoop):
    command = ('SELECT * FROM Points WHERE id=?', (chatId,))
    task = loop.addTask(command, lambda dbCur: dbCur.fetchone())
    return task.wait()


# client requests
def addNewClient(chatId, name, city, bindId, loop: SqlLoop = mainSqlLoop):
    def onProc(dbCur):
        if dbCur.fetchone() is None:  # create new client
            addTask = ('INSERT INTO Clients (id, name, city, bind) VALUES (?, ?, ?, ?)', (chatId, name, city, bindId))
            loop.addTask(addTask, lambda dbCur1: dbConn.commit())
        else:  # upadate info
            updTask = ('UPDATE Clients SET name = ?, city = ?, bind = ? WHERE id = ?', (name, city, bindId, chatId))
            loop.addTask(updTask, lambda dbCur1: dbConn.commit())

    checkTask = ('SELECT id FROM Clients WHERE id = ?', (chatId,))
    loop.addTask(checkTask, onProc)


def getClientById(userId, loop: SqlLoop = mainSqlLoop):
    command = ('SELECT * FROM Clients WHERE id=?', (userId,))
    task = loop.addTask(command, lambda dbCur: dbCur.fetchone())
    return task.wait()


def changeClientBind(clientId, newCity, newBind, loop: SqlLoop = mainSqlLoop):
    command = ('UPDATE Clients SET city = ?, bind = ? WHERE id = ?', (newCity, newBind, clientId))
    loop.addTask(command, lambda dbCur: dbConn.commit())


# consultant requests
def addNewConsultant(userId, name, loop: SqlLoop = mainSqlLoop):
    def onProc(dbCur):
        if dbCur.fetchone() is None:  # create new Consultant
            addTask = ('INSERT INTO Consultants (id, name) VALUES (?, ?)', (userId, name))
            loop.addTask(addTask, lambda dbCur1: dbConn.commit())
        else:
            updTask = ('UPDATE Consultants SET name = ? WHERE id = ?', (name, userId))
            loop.addTask(updTask, lambda dbCur1: dbConn.commit())

    checkTask = ('SELECT id FROM Consultants WHERE id = ?', (userId,))
    loop.addTask(checkTask, onProc)


def getConsultantById(userId, loop: SqlLoop = mainSqlLoop):
    command = ('SELECT * FROM Consultants WHERE id=?', (userId,))
    task = loop.addTask(command, lambda dbCur: dbCur.fetchone())
    return task.wait()


# task requests
def addNewTask(clientId, groupId, postId, loop: SqlLoop = mainSqlLoop):
    birthTime = time.time() // 60  # ? save time info in minutes
    command = ('INSERT INTO Tasks (clientId, groupId, postId, birthTime) VALUES (?, ?, ?, ?)',
               (clientId, groupId, postId, birthTime))
    loop.addTask(command, lambda dbCur: dbConn.commit())


def getTaskByClientId(clientId, loop: SqlLoop = mainSqlLoop):
    command = ('SELECT * FROM Tasks WHERE clientId=?', (clientId,))
    task = loop.addTask(command, lambda dbCur: dbCur.fetchone())
    return task.wait()


def changeTaskPost(prevGroup, prevId, newGroup, newId, loop: SqlLoop = mainSqlLoop):
    command = ('UPDATE Tasks SET groupId = ?, postId = ? WHERE groupId=? AND postId=?',
               (newGroup, newId, prevGroup, prevId))

    loop.addTask(command, lambda dbCur: dbConn.commit())


def getTaskByPost(groupId, postId, loop: SqlLoop = mainSqlLoop):
    command = ('SELECT * FROM Tasks WHERE groupId=? AND postId=?', (groupId, postId))
    task = loop.addTask(command, lambda dbCur: dbCur.fetchone())
    return task.wait()


def delTask(clientId, loop: SqlLoop = mainSqlLoop):
    command = ('DELETE FROM Tasks WHERE clientId=?', (clientId,))
    task = loop.addTask(command, lambda dbCur: dbConn.commit())
