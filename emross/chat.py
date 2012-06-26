import logging
import time
logger = logging.getLogger('emross-bot')

class Chat:
    URL = 'game/api_chat2.php'

    def __init__(self, api, bot):
        self.api = api
        self.bot = bot
        self.lineid = -1

    def check(self):
        if time.time() - self.bot.last_update > 60*5:
            return

        json = self.api.call(Chat.URL, lineid=self.lineid)

        try:
            msg = json['ret']['msg']
            self.lineid = msg[0]['line_id']
            self.parse_message(msg)
        except (AttributeError, IndexError):
            pass


    def parse_message(self, message):
        logger.debug(message)
