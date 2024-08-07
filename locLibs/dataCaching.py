import threading
import dbFunc


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
        return self.data

    def mark(self):
        self.topical = False
        self.data = None


class CachedPointsList(CachedData):
    def __init__(self):
        super().__init__(dbFunc.getPointsIdsSet_onlyDb)


cachedPointsList = CachedPointsList()


def clearPointsCache():
    cachedPointsList.mark()
