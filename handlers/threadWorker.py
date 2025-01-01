import queue
import threading
import logging
from functools import wraps

finishEv = threading.Event()


def worker(workQ: queue.Queue, logger: logging.Logger, ignoreErrs):
    while not workQ.empty() or not finishEv.is_set():
        try:
            func, args = workQ.get(timeout=240)
        except queue.Empty:
            continue
        try:
            func(*args)
        except Exception as e:
            logger.error(str(e))
            if not ignoreErrs:
                finishEv.set()
                raise e


class PoolHandlers:  # parse_key function is needed function for thread-friendly handlers
    def __init__(self, count: int, logger: logging.Logger, ignoreErrs: bool, parseKeyFunc, handler_name: str):
        self.taskHeaps = [queue.Queue() for _ in range(count)]
        self.workers = [threading.Thread(target=worker,
                                         args=(self.taskHeaps[i], logger, ignoreErrs),
                                         name=handler_name + ':' + str(i))
                        for i in range(len(self.taskHeaps))]
        self.parseKey = parseKeyFunc
        self.logger = logger

        for i in self.workers:
            i.start()

    def handlerDecorator(self, func):
        @wraps(func)
        def wrapper(*args):
            self.addTask(func, args)

        return wrapper

    def addTask(self, func, args):
        key = self.parseKey(*args)
        self.logger.debug(f'handlers_pool:{key} new task {func.__name__}')
        self.taskHeaps[key].put((func, args))
