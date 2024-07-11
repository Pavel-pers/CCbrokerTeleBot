import csv
import sqlite3

dbConn = sqlite3.connect('data/database.db', check_same_thread=False)
dbCur = dbConn.cursor()


def getCityList():
    cities = []
    with open('data/cities.csv', 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            cities.append(row[0])
    return cities


def addNewPoint(groupId, city, name, workHours):
    # TODO add validator
    dbCur.execute('INSERT INTO Points (id, city, name, workH) VALUES (?, ?, ?, ?)',
                  (groupId, city, name, workHours))
    dbConn.commit()


def addNewClient(chatId, name, city, bindId):
    dbCur.execute('SELECT id FROM Clients WHERE id = ?', (chatId,))
    if dbCur.fetchone() is None:  # create new client
        dbCur.execute('INSERT INTO Clients (id, name, city, bind) VALUES (?, ?, ?, ?)', (chatId, name, city, bindId))
    else:  # upadate info
        dbCur.execute('UPDATE Clients SET name = ?, city = ?, bind = ? WHERE id = ?', (name, city, bindId, chatId))
    dbConn.commit()


def addNewConsultant(userId, name):
    dbCur.execute('SELECT id FROM Consultants WHERE id = ?', (userId,))
    if dbCur.fetchone() is None:  # create new Consultant
        dbCur.execute('INSERT INTO Consultants (id, name) VALUES (?, ?)', (userId, name))
    else:
        dbCur.execute('UPDATE Consultants SET name = ? WHERE id = ?', (name, userId))
    dbConn.commit()


def getPointsByCity(city):
    dbCur.execute('SELECT * FROM Points WHERE city=?', (city,))
    return dbCur.fetchall()


def getPointById(chatId):
    dbCur.execute('SELECT * FROM Points WHERE id=?', (chatId,))
    return dbCur.fetchone()
