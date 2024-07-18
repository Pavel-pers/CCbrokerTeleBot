import telebot
from constants import UserStages, Inline


def regClient(bot: telebot.TeleBot):
    def decorator(func):
        def wrapper(msg: telebot.types.Message):
            if bot.get_state(msg.chat.id) is None:
                print(bot.get_state(msg.chat.id))
                return func(msg)
            elif bot.get_state(msg.chat.id) == UserStages.CLIENT_IN_CONVERSATION:
                inline = telebot.types.InlineKeyboardMarkup()
                inline.add(telebot.types.InlineKeyboardButton('end conversation', callback_data=Inline.POST_QUIT))
                bot.send_message(msg.chat.id, 'you are in conversation now', reply_markup=inline)
            else:
                bot.send_message(msg.chat.id, 'sorry, you cant do this now')

        return wrapper

    return decorator
