import code
import logging
import time
import threading
import Queue

logger = logging.getLogger(__name__)

from emross.api import EmrossWarApi
from emross.exceptions import BotException
from emross.utility.base import EmrossBaseObject
from emross.utility.helper import EmrossWarBot


class BotManager(object):
    WORKER_ERROR_WAIT = 15
    WORKER_ERROR_MAX_WAIT = 3600

    def __init__(self, console=False):
        self.players = []
        self.bots = []
        self.console = console
        self._initialised = False

    def bot(self, nickname=None, *args, **kwargs):
        """A helper function to locate a running bot"""

        for bot in self.bots:
            nick = bot.userinfo['nick']
            if nick.startswith(nickname) or nick.endswith(nickname):
                return bot

        return None

    def initialise_bots(self):
        if self._initialised:
            return

        EmrossWarApi.init_pool(len(self.players)*3)

        for player in self.players:
            api = EmrossWarApi(player.key, player.server, player.user_agent, player=player)
            bot = EmrossWarBot(api)

            self.bots.append(bot)

        self._initialised = True

    def run(self, func, scheduler=True):
        self.initialise_bots()

        workers = []
        for bot in self.bots:
            bot.session.start_time = time.time()

            if func:
                logger.info('Starting new bot thread for {0}'.format(bot.api.player))
                worker = threading.Thread(target=func, args=(bot,))
                worker.bot = bot
                worker.daemon = True
                worker.start()
            else:
                logger.info('No need to use a main thread for this worker!')
                worker = EmrossBaseObject(bot)

            workers.append(worker)
            if scheduler:
                bot.scheduler.start()


        def _inner_run():
            while len(workers) > 0:
                """
                If this wasn't here, our threads would all stop after.
                If we use thread.join() then it blocks the main-thread
                from receiving KeyboardInterrupt
                """
                for worker in workers[:]:
                    if worker.bot.blocked:
                        continue

                    error = None
                    try:
                        handled = set()
                        while True:
                            error = worker.bot.errors.get_nowait()
                            if error is None:
                                break

                            func, args, kwargs = error
                            if func in handled:
                                logger.debug('This error type has already been handled ({0})'.format(func))
                                worker.bot.errors.task_done()
                                continue

                            try:
                                func(*args, **kwargs)
                            except BotException as e:
                                worker.bot.runnable = False
                                workers.remove(worker)
                                self.bots.remove(worker.bot)
                                logger.exception(e)
                                worker.bot.errors.task_done()
                                logger.critical('Removed this bot instance from workers, marked for shutdown')
                            finally:
                                handled.add(func)
                    except Queue.Empty:
                        pass
                    except Exception as e:
                        logger.error(e)
                        t = self._handle_worker_errors(worker, error)
                        logger.debug('Error currently processing in {0}'.format(t))

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

            import settings
            sandbox = {'manager': self, 'settings': settings, 'bot':self.bot}
            code.interact(banner='EmrossWar Bot Management console', local=sandbox)
            raise KeyboardInterrupt
        else:
            # We can run this directly in this thread
            _inner_run()

    def _handle_worker_errors(self, worker, error, *args, **kwargs):
        logger.info('Error with worker, spawn new thread to resume error handling after delay')

        worker.bot.api.error_timer += self.WORKER_ERROR_WAIT
        delay = min(worker.bot.api.error_timer, self.WORKER_ERROR_MAX_WAIT)
        worker.bot.api.error_timer = delay

        def _handler():
            logger.debug('Bot blocked for {0} seconds.'.format(delay))
            worker.bot.blocked = True
            worker.bot.errors.put(error)
            time.sleep(delay)
            worker.bot.blocked = False
            worker.bot.errors.task_done()

        t = threading.Thread(target=_handler)
        t.daemon = True
        t.start()
        return t
