import logging
import time
logger = logging.getLogger(__name__)

from emross.utility.task import Task

class Chat(Task):
    INTERVAL = 5
    URL = 'game/api_chat2.php'

    def setup(self):
        self.lineid = -1

    def process(self):
        if time.time() - self.bot.last_update > 60*3:
            return

        json = self.bot.api.call(self.__class__.URL, lineid=self.lineid)

        try:
            msg = json['ret']['msg']
            self.lineid = msg[0]['line_id']
            self.parse_message(msg)
        except (AttributeError, IndexError):
            pass


    def parse_message(self, message):
        """
        The message may contain useful info such as incoming loot notifcations.
        Maybe we can use this in future.
        """
        pass
        #logger.debug(message)
