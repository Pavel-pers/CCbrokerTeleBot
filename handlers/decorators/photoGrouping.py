import dataclasses
import logging

import telebot
import threading
import time
import queue
from constants import Config
from dataclasses import dataclass, field
from typing import Any

delPendQ = queue.PriorityQueue()
waitingMedia = dict()
mediaInfoLock = threading.Lock()


@dataclass(order=True)
class PendingMedia:
    deadline: float
    lstLen: int = field(compare=False)
    mediaId: int = field(compare=False)
    media: list = field(compare=False)


def photoCollector():
    while True:
        top: PendingMedia = delPendQ.get()
        if time.time() > top.deadline:
            with mediaInfoLock:
                if len(top.media) == top.lstLen:
                    callback = waitingMedia[top.mediaId][1]
                    waitingMedia.pop(top.mediaId)
                    callback(top.media)
        else:
            delPendQ.put(top)
            time.sleep(0.1)


def genNewMsg(msg: telebot.types.Message, media):
    if len(media) == 1:
        return msg

    msg.photo = media[:10]
    for i in range(len(msg.photo)):
        if msg.photo[i].caption:
            msg.photo[0], msg.photo[i] = msg.photo[i], msg.photo[0]
            break

    msg.content_type = 'media_group'
    return msg


def parseImgGroup(handler, firstMsg: telebot.types.Message):
    mediaId = int(firstMsg.media_group_id)
    media = [telebot.types.InputMediaPhoto(media=firstMsg.photo[0].file_id, caption=firstMsg.text or firstMsg.caption)]
    with mediaInfoLock:
        waitingMedia[mediaId] = (media, lambda recMedia: handler(genNewMsg(msg=firstMsg, media=recMedia)))
        delPendQ.put(PendingMedia(time.time() + 0.5, len(media), int(mediaId), media))


def isWaiting(mediaId, blocking):
    if mediaId is None:
        return False
    if blocking:
        mediaInfoLock.acquire()
        result = int(mediaId) in waitingMedia
        if not result:
            mediaInfoLock.release()
        return result
    else:
        with mediaInfoLock:
            return int(mediaId) in waitingMedia


def startListen(bot: telebot.TeleBot, logger: logging.Logger):
    threading.Thread(target=photoCollector, daemon=True).start()

    @bot.message_handler(content_types=['photo'], func=lambda msg: isWaiting(msg.media_group_id, True))
    def recievePhoto(msg: telebot.types.Message):
        media = waitingMedia[int(msg.media_group_id)][0]
        media.append(telebot.types.InputMediaPhoto(media=msg.photo[0].file_id, caption=msg.text or msg.caption))
        delPendQ.put(PendingMedia(time.time() + 0.5, len(media), int(msg.media_group_id), media))
        mediaInfoLock.release()


def decorator(handler):
    def wrapper(msg: telebot.types.Message):
        if msg.content_type != 'photo' or msg.media_group_id is None:
            return handler(msg)
        parseImgGroup(handler, msg)
        return None

    return wrapper
