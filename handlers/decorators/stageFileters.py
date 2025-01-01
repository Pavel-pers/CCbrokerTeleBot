import telebot
from constants import UserStages, Replicas


def regClient(bot: telebot.TeleBot):
    def decorator(func):
        def wrapper(msg: telebot.types.Message):
            if bot.get_state(msg.chat.id) is None:
                return func(msg)
            elif bot.get_state(msg.chat.id) == UserStages.CLIENT_IN_CONVERSATION:
                bot.send_message(msg.chat.id, Replicas.ERROR_ALREADY_IN_CONVERASTION)
            else:
                bot.send_message(msg.chat.id, Replicas.UNDEFINED_ERROR)

        return wrapper

    return decorator
