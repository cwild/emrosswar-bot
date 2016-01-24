import logging

logger = logging.getLogger(__name__)

import emross
from emross.api import EmrossWarApi, agent, cache_ready
from emross.utility.helper import EmrossWarBot


DEFAULT_POOL_SIZE = 5


class BotManager(object):

    def __init__(self, console=False, settings={}, **kwargs):
        self.bots = []
        self.console = console
        self.kwargs = kwargs
        self.socket = None
        self.settings = settings

    def create_bot_from_player(self, player, **kwargs):
        logger.debug('Adding new bot for %s', player)

        api = EmrossWarApi(player.key, player.server, player.user_agent, player=player)
        bot = EmrossWarBot(api, settings=self.settings, **kwargs)
        self.bots.append(bot)

    def run(self, workhorse=True):
        emross.reactor.addSystemEventTrigger('before', 'shutdown', self.shutdown)

        pool = self.kwargs.get('poolsize') or DEFAULT_POOL_SIZE
        agent._agent._pool.maxPersistentPerHost = pool

        for bot in self.bots:
            cache_ready(bot.startup)

        if workhorse:
            emross.reactor.run()

    def shutdown(self):
        """
        Initiate shutdown. Each bot should save Session data before stopping.
        """
        for bot in self.bots:
            bot.shutdown()

        logger.info('Exiting')
