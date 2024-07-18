import logging
import queue
import threading
import time
import telebot


class TeleBotBanF(telebot.TeleBot):
    def __init__(self, *args, **kwargs):
        if 'block_list' in kwargs:
            self.blockUsers = kwargs['block_list']
            kwargs.pop('block_list')
        else:
            self.blockUsers = set()
        super().__init__(*args, **kwargs)

    def get_updates(self, *args, **kwargs):
        jsonEvents = telebot.apihelper.get_updates(self.token, *args, **kwargs)
        filtData = []
        for event in jsonEvents:
            if 'message' in event and event['message']['chat']['id'] in self.blockUsers:
                self.last_update_id = event['update_id']
            else:
                filtData.append(telebot.types.Update.de_json(event))
        return filtData

    def block_user(self, userId):
        self.blockUsers.add(userId)


class DataForInlineCB:
    def __init__(self):
        super().__init__()
        self.dict = dict()
        self.delPlans = queue.PriorityQueue()
        threading.Thread(target=self.garbCollect, daemon=True).start()

    def add(self, key, data, aliveTime):
        self.dict[key] = data
        aliveUntil = int(time.time()) + aliveTime
        self.delPlans.put((aliveUntil, key))

    def get(self, key):
        data = self.dict.get(key, None)
        if data is not None:
            self.dict.pop(key)
        return data

    def garbCollect(self):
        while True:
            while not self.delPlans.empty():
                aliveUntil, key = self.delPlans.get()
                if int(time.time()) < aliveUntil:
                    self.delPlans.put((aliveUntil, key))
                    break
                self.dict.pop(key, None)
            time.sleep(1)


class PendingMessages:
    def __init__(self):
        self.pendingQ = {}

    def add(self, chatId, replyId, callback):
        self.pendingQ[(chatId, replyId)].append(callback)

    def isWaiting(self, chatId, replyId):
        return (chatId, replyId) in self.pendingQ

    def newAwait(self, chatId, replyId):
        self.pendingQ[(chatId, replyId)] = []

    def processCB(self, keyChat, keyReply, cbChat, cbReply):
        cbLst = self.pendingQ.get((keyChat, keyReply), [])
        for callback in cbLst:
            callback(cbChat, cbReply)
        self.pendingQ.pop((keyChat, keyReply), None)


class MsgContent:
    def __init__(self, message: telebot.types.Message):
        self.content_type = message.content_type
        self.text = message.text
        self.caption = message.caption
        self.photo = message.photo
        self.document = message.document
        self.audio = message.audio
        self.video = message.video
        self.voice = message.voice
        self.video_note = message.video_note
        self.sticker = message.sticker
        self.media_group_id = message.media_group_id
