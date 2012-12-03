import logging
import time
import threading

logger = logging.getLogger(__name__)

from emross.api import EmrossWarApi
from emross.utility.helper import EmrossWarBot


class BotManager(object):
    def __init__(self):
        self.players = []
        self.bots = []

    def run(self, func):
        for player in self.players:
            api = EmrossWarApi(player.key, player.server, player.user_agent)
            bot = EmrossWarBot(api)
            self.bots.append(bot)

        workers = []
        for bot in self.bots:
            logger.info('Starting new bot thread for api_key=%s' % bot.api.api_key)
            worker = threading.Thread(target=func, args=(bot,))
            worker.daemon = True
            worker.start()
            workers.append(worker)


        while True:
            """
            If this wasn't here, our threads would all stop after.
            If we use thread.join() then it blocks the main-thread
            from receiving KeyboardInterrupt
            """
            time.sleep(100)
