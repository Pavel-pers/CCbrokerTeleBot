import csv
import sqlite3

import threading
import queue
import logging

import time
from sys import argv as sysArgv

dbLogger = logging.getLogger('DB_main')
handler = logging.FileHandler('log/.log', mode='a')
formatter = logging.Formatter('[%(asctime)s](%(name)s)%(levelname)s:%(message)s', '%H:%M:%S')
handler.setFormatter(formatter)
dbLogger.addHandler(handler)
dbLogger.setLevel(logging.DEBUG)

dbConn = sqlite3.connect('data/database.db', check_same_thread=False)
if __name__ == "__main__":
    print('preparing tables')
    dbCurr = dbConn.cursor()
    dbCurr.execute("""CREATE TABLE IF NOT EXISTS Tasks(
        clientId INTEGER PRIMARY KEY,
        groupId INTEGER,
        postId INTEGER,
        topicId INTEGER NOT NULL,
        activeIds TEXT DEFAULT "" NOT NULL,
        lastActiveTime INTEGER
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
        ansCnt INTEGER DEFAULT 0,
        rateSm INTEGER DEFAULT 0,
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

    print("done")


# -block list functions
#   -get
def getBlockList():
    banUsers = set()
    with open('data/banList.txt', 'r') as f:
        for l in f:
            banUsers.add(int(l.strip()))
    return banUsers


#   -add
def addBlockUser(userId):
    with open('data/banList.txt', 'a') as f:
        f.write(str(userId) + '\n')


# -csv functions
# -csv functions
class CachedData:
    def __init__(self):
        # init cities
        self.cities = []
        with open('data/cities.csv', 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                self.cities.append((row[0], row[1]))
        # init reg cities
        self.regCities = []
        with open('data/regCities.csv', 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                self.regCities.append(row[0])


cachedData = CachedData()
csvLock = threading.Lock()


def getCities():
    return cachedData.cities


def getRegCities():
    return cachedData.regCities


def addRegCity(city):
    dbLogger.debug('add ' + city)
    cities = cachedData.regCities  # linked to cach data
    with csvLock:
        if city not in cities:
            cities.append(city)
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
    cities = cachedData.regCities
    with csvLock:
        citiesC = []
        with open('data/regCities.csv', 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                row[1] = int(row[1])
                if row[0] == city:
                    row[1] -= 1
                if row[1] > 0:
                    citiesC.append(row)
                else:
                    cities.remove(row[0])
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
        request = None
        if dbLogger.level == logging.DEBUG:
            def modfFunc(dbCur):
                dbLogger.debug('processed-' + str(commInfo))
                return onProcesed(dbCur)

            request = SqlRequest(commInfo, modfFunc)
        else:
            request = SqlRequest(commInfo, onProcesed)

        try:
            self.workQ.put_nowait(request)
        except queue.Full:
            self.logger.warning('queue full')
            self.workQ.put(request)
        dbLogger.debug('add task-' + str(commInfo))
        return request

    def killLoop(self, blocking=True):
        self.logger.info('stopping loop')
        self.finishEv.set()
        if blocking:
            self.workTh.join()
            self.logger.info('stopped loop')


mainSqlLoop = SqlLoop(dbLogger)  # TODO make on each table different loops


# general sql requests
def initTable(funcs: list, tableName: str, loop: SqlLoop = mainSqlLoop):
    command = ('SELECT * FROM ' + tableName,)

    def processRows(dbCur: sqlite3.Cursor):
        for row in dbCur:
            for f in funcs:
                f(row)

    loop.addTask(command, processRows)


def getAllData(tableName: str, reqRows: tuple | None = None, loop: SqlLoop = mainSqlLoop):
    if reqRows is None:
        reqRows = '*'
    else:
        reqRows = ', '.join(reqRows)

    command = (f'SELECT {reqRows} FROM ' + tableName,)
    return loop.addTask(command, lambda dbCur: dbCur.fetchall()).wait()


# point requests
def addNewPoint(groupId, city, name, workHours: str, loop: SqlLoop = mainSqlLoop):
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


def delClient(clientId, loop: SqlLoop = mainSqlLoop):
    command = ('DELETE FROM Clients WHERE id=?', (clientId,))
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


def addRateConsultant(consultantId: int, rate: int, loop: SqlLoop = mainSqlLoop):
    rate = int(rate)
    getComm = ('SELECT ansCnt,rateSm FROM Consultants WHERE id=?', (consultantId,))

    def onProc(dbCur: sqlite3.Cursor):
        ansCnt, rateSm = dbCur.fetchone()
        updComm = ('UPDATE Consultants SET ansCnt=?, rateSm=? WHERE id=?', (ansCnt + 1, rateSm + rate, consultantId))
        loop.addTask(updComm, lambda dbCur1: dbConn.commit())

    loop.addTask(getComm, onProc)


# task requests
def addNewTask(clientId, groupId, postId, topicId, loop: SqlLoop = mainSqlLoop):
    birthTime = int(time.time())  # ? save time info in minutes
    command = ('INSERT INTO Tasks (clientId, groupId, postId, topicId, lastActiveTime) VALUES (?, ?, ?, ?, ?)',
               (clientId, groupId, postId, topicId, birthTime))
    loop.addTask(command, lambda dbCur: dbConn.commit())


def getTaskByClientId(clientId, loop: SqlLoop = mainSqlLoop):
    command = ('SELECT * FROM Tasks WHERE clientId=?', (clientId,))
    task = loop.addTask(command, lambda dbCur: dbCur.fetchone())
    return task.wait()


def changeTaskByPost(prevGroup, prevId, newGroup, newId, loop: SqlLoop = mainSqlLoop):
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


def addNewActive(clientId, activeId, loop: SqlLoop = mainSqlLoop):  # TODO validate func
    getComm = ('SELECT activeIds FROM Tasks WHERE clientId = ?', (int(clientId),))

    def onProc(dbCur: sqlite3.Cursor):
        activeIds = dbCur.fetchone()[0]
        if activeId not in activeIds.split(';'):
            addComm = (
                'UPDATE Tasks SET activeIds = ? WHERE  clientId = ?', (activeIds + str(activeId) + ';', int(clientId)))
            loop.addTask(addComm, lambda dbCur1: dbConn.commit())

    loop.addTask(getComm, onProc)


def updActiveTime(clientId, loop: SqlLoop = mainSqlLoop):
    curTime = int(time.time())
    loop.addTask(('UPDATE Tasks SET lastActiveTime = ? WHERE clientId = ?', (curTime, clientId)),
                 lambda dbCur: dbConn.commit())


def getActiveIdsById(clientId, loop: SqlLoop = mainSqlLoop):
    getComm = ('SELECT activeIds FROM Tasks WHERE clientId=?', (clientId,))
    task = loop.addTask(getComm, lambda dbCur: dbCur.fetchone()[0])
    return task.wait().split(';')[:-1]


if __name__ == '__main__' and len(sysArgv) > 1 and sysArgv[1] == '-t':
    mainSqlLoop.start()
    funcDict = globals()
    funcName = ''
    while funcName != 'close':
        funcName = input('func name:')
        if funcName not in funcDict:
            continue
        func = funcDict[funcName]
        args = input('args({0}):'.format(','.join(func.__code__.co_varnames[:func.__code__.co_argcount]))).split(',')
        print(func(*args) if args != [''] else func())

    mainSqlLoop.killLoop(True)
