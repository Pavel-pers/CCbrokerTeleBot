"""
works only on non-threaded handlers(listeners) yet
"""
from telebot import types


def _formatKey(key):
    if type(key) is types.Message:
        return key.chat.id, key.id
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
                return func(*args)
            return None

        return wrapper

    return decorator
