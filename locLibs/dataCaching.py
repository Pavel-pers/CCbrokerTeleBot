import threading


class CachedData:
    def __init__(self, updateFunc):
        self.lock = threading.Lock()
        self.data = None
        self.topical = False
        self.updateFunc = updateFunc

    def get(self):
        if not self.topical:
            self.data = self.updateFunc()
            self.topical = True
        return self.data.copy()

    def mark(self):
        self.topical = False
        self.data = None
