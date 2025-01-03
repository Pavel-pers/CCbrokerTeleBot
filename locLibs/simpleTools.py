import time
from re import compile


def timezoneConv(strTime: str, timezone: str):
    h, m = strTime.split(':')
    ms = int(h) * 60 + int(m)
    if timezone[0] == '-':
        ms += int(timezone[1:3]) * 60 + int(timezone[3:5])
    else:
        ms -= int(timezone[1:3]) * 60 + int(timezone[3:5])
    ms %= 60 * 24
    h = str(ms // 60).zfill(2)
    m = str(ms % 60).zfill(2)
    return h + ':' + m


def distToTimeSgm(timeSegmentGmt: str, timeS=None):
    start, finish = timeSegmentGmt.split('-')
    start = tuple(map(int, start.split(':')))
    finish = tuple(map(int, finish.split(':')))
    tm = time.gmtime(timeS)
    curTime = (tm.tm_hour, tm.tm_min)
    if start > finish:
        if finish >= curTime or start <= curTime:
            return 0
    else:
        if start <= curTime <= finish:
            return 0
    return ((start[0] * 60 + start[1]) - (curTime[0] * 60 + curTime[1])) % (24 * 60)


workH_pattern = compile('(?:[01][0-9]|2[0-3]):[0-5][0-9]-(?:[01][0-9]|2[0-3]):[0-5][0-9]$')


def genMention(name, tg_id):  # returns message in html parse mod
    return f"<a href = 'tg://user?id={tg_id}'> {name} </a>"
