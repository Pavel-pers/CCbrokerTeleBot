class Inline:
    POST_CANCEL = 'cancelPost'
    POST_CONTINUE = 'continuePost'
    POST_QUIT = 'quitPost'
    RATE_PREF = 'rate:'


class UserStages:
    CLIENT_REDIR = 1
    CLIENT_IN_CONVERSATION = 2


class Config:
    ALLOWED_CONTENT = ['text', 'photo', 'document', 'audio', 'video', 'voice', 'video_note', 'sticker']
    INLINE_DELAY = 60 * 30
    NEXT_PHOTO_WAIT_TIME = 0.5
    REMINDER_DELAY = 5  # ! debug


class Emoji:
    RATE = ['', '1\u20E3', '2\u20E3', '3\u20E3', '4\u20E3', '5\u20E3']
    OPEN_TASK = '5238156910363950406'
    CLOSED_TASK = '5237699328843200968'


FORUM_CHAT = -1002176286003
