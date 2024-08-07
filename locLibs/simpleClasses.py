import logging
import queue
import threading
import time
import telebot
from constants import Config


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


class PendingItems:
    def __init__(self, dataClass):
        self.lock = threading.Lock()
        self.delPlans = queue.PriorityQueue()
        self.data = dataClass()
        threading.Thread(target=self.garbCollecter, daemon=True).start()

    def garbCollecter(self):
        while True:
            while not self.delPlans.empty():
                with self.lock:
                    aliveUntil, key = self.delPlans.get()
                    if int(time.time()) < aliveUntil:
                        self.delPlans.put((aliveUntil, key))
                        break
                    self.dict.pop(key, None)
            time.sleep(60 * 5)

    def add(self, *args, **kwargs):
        raise NotImplementedError

    def get(self, *args, **kwargs):
        raise NotImplementedError


class DataForCallBacks(PendingItems):
    def __init__(self):
        super().__init__(dict)
        self.data: dict

    def add(self, key, data, aliveTime):
        with self.lock:
            self.data[key] = data
            aliveUntil = int(time.time()) + aliveTime
            self.delPlans.put((aliveUntil, key))

    def get(self, key):
        with self.lock:
            data = self.data.pop(key, None)
            return data


class PendingPermissions(PendingItems):
    def __init__(self):
        super().__init__(set)
        self.data: set

    def add(self, key):
        with self.lock:
            self.data.add(key)
            aliveUntil = int(time.time()) + Config.PERMITION_WAIT
            self.delPlans.put((aliveUntil, key))

    def get(self, key):
        if key in self.data:
            self.data.remove(key)
            return True
        return False


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


class ShrinkedChatInfo:
    def __init__(self, chat: telebot.types.Chat):
        self.id = chat.id


class MsgContent:
    def __init__(self, message: telebot.types.Message):
        self.id = message.id
        self.chat = ShrinkedChatInfo(message.chat)
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


class Handlers:
    def set_bot(self, bot):
        self.bot = bot

    def set_logger(self, logger):
        self.logger = logger

    def __init__(self):
        self.bot: telebot.TeleBot = None
        self.logger: logging.Logger = None
