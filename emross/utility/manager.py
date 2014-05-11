import code
import logging
import time
import threading
import Queue

from multiprocessing.dummy import Process

logger = logging.getLogger(__name__)

from emross.api import EmrossWarApi
from emross.exceptions import BotException
from emross.utility.base import EmrossBaseObject
from emross.utility.helper import EmrossWarBot
from emross.utility.socket_handlers import JsonSocketHandler


DEFAULT_POOL_SIZE = 10

# The delay between each completed cycle of our bot handlers
ERROR_TICK = 1
WORKER_TICK = 0.1

# When an error is encountered, it is handled in a separate thread
WORKER_ERROR_WAIT = 15
WORKER_ERROR_MAX_WAIT = 3600


def _bot_consumer(queue):
    while True:
        try:
            func, args = queue.get()
            func(*args)
        except Exception as e:
            logger.exception(e)

def _do_work(bot, *args, **kwargs):
    bot.builder.process(*args, **kwargs)

def _bot_runner(queue, bots, **kwargs):
    while len(bots):
        for bot in bots:
            try:
                if not bot.is_initialised:
                    def _bot_init(_bot):
                        # Let's get the ball rolling!
                        with _bot.lock:
                            if _bot.is_initialised or _bot.closing:
                                return
                            try:
                                logger.debug('init id={0}'.format(_bot.userinfo['id']))
                                _bot.is_initialised = True
                            except KeyError as e:
                                logger.debug(e)

                    # Delegate to a worker
                    queue.put((_bot_init, (bot,)))
                    continue

                if bot.blocked or not bot.is_play_time():
                    continue

                for task, jobs in bot.tasks.iteritems():
                    if task not in bot.builder.running_build_stages:
                        bot.builder.running_build_stages.add(task)
                        queue.put((_do_work, (bot, jobs, task)))
            except Exception as e:
                logger.exception(e)
                continue

        time.sleep(WORKER_TICK)

def _error_checker(workers, bots):
    """
    Continuously check each bot for errors and handle them sequentially.
    """
    while len(workers):
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
                        bots.remove(worker.bot)
                        logger.exception(e)
                        worker.bot.errors.task_done()
                        logger.critical('Removed this bot instance from workers, marked for shutdown')
                    finally:
                        handled.add(func)
            except Queue.Empty:
                pass
            except Exception as e:
                logger.error(e)
                t = _handle_worker_errors(worker, error)
                logger.debug('Error currently processing in {0}'.format(t))

        # After checking every bot, take a quick breath!
        time.sleep(ERROR_TICK)


def _handle_worker_errors(worker, error, *args, **kwargs):
    logger.info('Error with worker, spawn new thread to resume error handling after delay')

    worker.bot.api.error_timer += WORKER_ERROR_WAIT
    delay = min(worker.bot.api.error_timer, WORKER_ERROR_MAX_WAIT)
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



class BotManager(object):

    def __init__(self, console=False, settings={}, **kwargs):
        self.players = []
        self.bots = []
        self.console = console
        self.kwargs = kwargs
        self.socket = None
        self.settings = settings

    def bot(self, nickname=None, *args, **kwargs):
        """A helper function to locate a running bot"""

        for bot in self.bots:
            nick = bot.userinfo['nick']
            if nick.startswith(nickname) or nick.endswith(nickname):
                return bot

    def initialise_bots(self, **kwargs):
        for player in self.players:
            api = EmrossWarApi(player.key, player.server, player.user_agent, player=player)

            self.bots.append(
                EmrossWarBot(api, **kwargs)
            )

    def run(self, func=None, workhorse=True):

        if self.kwargs.get('socket'):
            try:
                from emross.utility.socket import establish_connection
                self.socket = establish_connection()

                socket_handler = JsonSocketHandler(self.socket, self.bots)
                socket_handler.daemon = True
                socket_handler.start()
            except Exception as e:
                logger.exception(e)


        self.initialise_bots(
            socket_writer=getattr(self.socket, 'queue_out', None),
            settings=self.settings
        )

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
                logger.debug('No need to use a main thread for this worker!')
                worker = EmrossBaseObject(bot)

            workers.append(worker)


        """
        Now we can start the main event loop.
        If we are running a console then the `code.interact` will block
        so we need to spawn a thread to process each bot's error queue.
        """

        error_thread = Process(target=_error_checker, args=(workers, self.bots))
        error_thread.daemon = True
        error_thread.start()

        processes = self.kwargs.get('processes') or DEFAULT_POOL_SIZE

        queue = Queue.Queue(processes)
        for i in range(processes):
            t = Process(target=_bot_consumer, args=(queue,))
            t.daemon = True
            t.start()

        if self.console:
            worker = Process(target=_bot_runner, args=(queue, self.bots),
                                kwargs=self.kwargs)
            worker.daemon = True
            worker.start()

            import settings
            sandbox = {'manager': self, 'settings': settings, 'bot':self.bot}
            code.interact(banner='EmrossWar Bot Management console', local=sandbox)
            raise KeyboardInterrupt
        elif workhorse:
            # We can run this directly in this thread
            _bot_runner(queue, self.bots, **self.kwargs)
