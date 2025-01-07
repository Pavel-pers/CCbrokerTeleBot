import enum

ALLOWED_CONTENT = ['text', 'photo', 'document', 'audio', 'video', 'voice', 'video_note', 'sticker']
INLINE_DELAY = 60 * 30
NEXT_PHOTO_WAIT_TIME = 0.5
REMINDER_DELAY = 60 * 45
BONUS_TIME = 60 * 60
PERMITION_WAIT = 60 * 5
FORUM_CHAT = -1002176286003
INVITE_LINK_PREFIX = "invite:"
ALLOWED_UPDATES = ['message', 'edited_message', 'channel_post', 'my_chat_member', 'chat_member', 'chat_join_request',
                   'callback_query']


class PointType(enum.Enum):
    retail = 0
    wholesale = 1
    service_station = 2

    def __str__(self):
        if self.value == PointType.retail.value:
            return "Розница"
        elif self.value == PointType.wholesale.value:
            return "ОПТ"
        elif self.value == PointType.service_station.value:
            return "СТО"
        else:
            raise NotImplementedError
