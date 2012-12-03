import logging
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
            logger.info('Starting new bot thread')
            worker = threading.Thread(target=func, args=(bot,))
            worker.daemon = True
            worker.start()
            workers.append(worker)


        while len(workers) > 0:
            try:
                # Join all threads using a timeout so it doesn't block
                # Filter out threads which have been joined or are None
                workers = [t.join(1000) for t in workers if t is not None and t.isAlive()]
            except KeyboardInterrupt:
                for t in workers:
                    t.kill_received = True
                raise
