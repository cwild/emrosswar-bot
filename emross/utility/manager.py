import code
import logging
import time
import threading
import Queue

logger = logging.getLogger(__name__)

from emross.api import EmrossWarApi
from emross.utility.helper import EmrossWarBot

import settings

class BotManager(object):
    def __init__(self, console=False):
        self.players = []
        self.bots = []
        self.console = console

    def bot(self, nickname=None, *args, **kwargs):
        """A helper function to locate a running bot"""

        for bot in self.bots:
            nick = bot.userinfo['nick']
            if nick.startswith(nickname) or nick.endswith(nickname):
                return bot

        return None

    def initialise_bots(self):
        for player in self.players:
            api = EmrossWarApi(player.key, player.server, player.user_agent, player=player)
            bot = EmrossWarBot(api)

            self.bots.append(bot)

    def run(self, func):
        self.initialise_bots()

        workers = []
        for bot in self.bots:
            logger.info('Starting new bot thread for %s' % bot.api.player)
            worker = threading.Thread(target=func, args=(bot,))
            worker.bot = bot
            worker.daemon = True
            worker.start()
            workers.append(worker)


        def _inner_run():
            while len(workers) > 0:
                """
                If this wasn't here, our threads would all stop after.
                If we use thread.join() then it blocks the main-thread
                from receiving KeyboardInterrupt
                """
                for worker in workers[:]:
                    try:
                        handled = set()
                        while True:
                            error = worker.bot.errors.get_nowait()
                            if error is None:
                                break
                            else:
                                func, args = error
                                if func in handled:
                                    logger.debug('This error type has already been handled')
                                    worker.bot.errors.task_done()
                                else:
                                    func(*args)
                                    handled.add(func)
                    except Queue.Empty:
                        pass
                    except Exception as e:
                        logger.exception(e)
                        workers.remove(worker)
                        logger.critical('Removed this bot instance')

                    time.sleep(2)


        """
        Now we can start the main event loop.
        If we are running a console then the `code.interact` will block
        so we need to spawn a thread to process each bot's error queue.
        """
        if self.console:
            worker = threading.Thread(target=_inner_run)
            worker.daemon = True
            worker.start()

            sandbox = {'manager': self, 'settings': settings, 'bot':self.bot}
            code.interact(banner='EmrossWar Bot Management console', local=sandbox)
            raise KeyboardInterrupt
        else:
            # We can run this directly in this thread
            _inner_run()
