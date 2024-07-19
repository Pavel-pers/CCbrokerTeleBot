class Inline:
    POST_CANCEL = 'cancelPost'
    POST_CONTINUE = 'continuePost'
    POST_QUIT = 'quitPost'


class UserStages:
    CLIENT_REDIR = 1
    CLIENT_IN_CONVERSATION = 2


class Config:
    ALLOWED_CONTENT = ['text', 'photo', 'document', 'audio', 'video', 'voice', 'video_note', 'sticker']
    INLINE_DELAY = 60 * 30
    NEXT_PHOTO_WAIT_TIME = 0.5
