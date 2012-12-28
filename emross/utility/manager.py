import code
import logging
import time
import threading

logger = logging.getLogger(__name__)

from emross.api import EmrossWarApi
from emross.utility.helper import EmrossWarBot

import settings

class BotManager(object):
    def __init__(self, console=False):
        self.players = []
        self.bots = []
        self.console = console

    def bot(self, needle=None, *args, **kwargs):
        """A helper function to locate a running bot"""

        for bot in self.bots:
            nick = bot.userinfo['nick']
            if nick.startswith(needle) or nick.endswith(needle):
                return bot

        return None

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

        if self.console:
            sandbox = {'manager': self, 'settings': settings, 'bot':self.bot}
            code.interact(banner='EmrossWar Bot Management console', local=sandbox)
            raise KeyboardInterrupt
        else:
            while True:
                """
                If this wasn't here, our threads would all stop after.
                If we use thread.join() then it blocks the main-thread
                from receiving KeyboardInterrupt
                """
                time.sleep(100)
