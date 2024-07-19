import threading
import functools
from time import sleep


class InProcHandlers:
    class HandlerLock:
        def __init__(self):
            self.lock = threading.Lock()
            self.count = 0

    def __init__(self):
        self.lock = threading.Lock()
        self.dict = dict()

    def acquire(self, key):
        with self.lock:
            lock = self.dict.get(key, None)
            if lock is None:
                lock = InProcHandlers.HandlerLock()
                self.dict[key] = lock
            lock.count += 1
        lock.lock.acquire()

    def release(self, key):
        with self.lock:
            lock = self.dict[key]
            lock.count -= 1
            lock.lock.release()

            if lock.count == 0:
                self.dict.pop(key)


def thread_friendly(cellLocker: InProcHandlers, parseKey):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            """
            :return: thread-friendly function
            """
            key = parseKey(args)
            cellLocker.acquire(key)
            result = func(*args, **kwargs)
            cellLocker.release(key)
            return result

        return wrapper

    return decorator
