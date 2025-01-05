import typing

import telebot
import logging

from handlers import threadWorker
from locLibs import simpleClasses, dbFunc
from constants import Config


class ChannelHandler(simpleClasses.Handlers):
    def forwardPostGenerator(self, channel_id, post_id) -> typing.Callable[[int], bool]:
        def forwardPost(client_id) -> bool:
            try:
                self.bot.forward_message(client_id, channel_id, post_id)
            except telebot.apihelper.ApiTelegramException as e:
                logging.warning("couldn't forward post: ", e.description)
                return False

            offer_to_unsubscribe_markup = telebot.types.InlineKeyboardMarkup()
            offer_to_unsubscribe_button = (
                telebot.types.InlineKeyboardButton('unsubscribe', callback_data='unsubscribe:' + str(client_id)))
            offer_to_unsubscribe_markup.add(offer_to_unsubscribe_button)
            self.bot.send_message(client_id, 'unsubscribe?', reply_markup=offer_to_unsubscribe_markup)
            return True

        return forwardPost

    def newPostHadnler(self, msg: telebot.types.Message):
        client_filter = Config.CHANNEL_FILTER[msg.chat.id]
        repost_count = dbFunc.iterateSubscribers(client_filter, self.forwardPostGenerator(msg.chat.id, msg.message_id))
        self.bot.reply_to(msg, 'replied to ' + str(repost_count) + ' uesrs')
