"""
works only on non-threaded handlers(listeners) yet
"""
import threading
import logging
from telebot import types

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


def _formatKey(key):
    if type(key) is types.Message:
        return (key.chat.id, key.id)
    elif type(key) is types.CallbackQuery:
        return (key.id,)
    else:
        raise 'incorrect key'


class PrevisousKeys:
    prevKey = None

    def isProcessed(self, key):
        key = _formatKey(key)
        return key == self.prevKey

    def addKey(self, key):
        key = _formatKey(key)
        self.prevKey = key


previsousKeyGlobal = PrevisousKeys()


def getDecorator(keyInd=0, prevKey=previsousKeyGlobal):
    def decorator(func):
        def wrapper(*args):
            key = args[keyInd]
            if not prevKey.isProcessed(key):
                prevKey.addKey(key)
                logger.debug(func.__name__ + ' processed ' + str(_formatKey(key)))
                return func(*args)
            logger.debug(func.__name__ + ' skipped ' + str(_formatKey(key)))
            return None

        return wrapper

    return decorator
