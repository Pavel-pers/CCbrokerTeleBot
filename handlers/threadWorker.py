import queue
import threading
import logging

finishEv = threading.Event()


def worker(workQ: queue.Queue, logger: logging.Logger, ignoreErrs):
    while not workQ.empty() or not finishEv.is_set():
        try:
            func, args = workQ.get(timeout=60)
        except queue.Empty:
            continue
        try:
            func(*args)
        except Exception as e:
            logger.error(str(e))
            if not ignoreErrs:
                finishEv.set()
                raise e
