import telebot
from constants import UserStages, Inline


def regClient(bot: telebot.TeleBot):
    def decorator(func):
        def wrapper(msg: telebot.types.Message):
            if bot.get_state(msg.chat.id) is None:
                return func(msg)
            elif bot.get_state(msg.chat.id) == UserStages.CLIENT_IN_CONVERSATION:
                bot.send_message(msg.chat.id, 'you are in conversation now, ask consultant to close')
            else:
                bot.send_message(msg.chat.id, 'sorry, you cant do this now')

        return wrapper

    return decorator
