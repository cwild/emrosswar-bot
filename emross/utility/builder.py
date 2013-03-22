import logging
logger = logging.getLogger(__name__)

import threading
import time

class BuildManager(object):

    def __init__(self, bot, *args, **kwargs):
        self.bot = bot
        self.tasks = {}
        self.lock = threading.Lock()
        super(BuildManager, self).__init__(*args, **kwargs)

    def task(self, task_class):
        with self.lock:
            try:
                handler = self.tasks[task_class]
            except KeyError, e:
                handler = self.tasks[task_class] = task_class(self.bot)
            except TypeError, e:
                logger.exception(e)
                raise e
        return handler

    def process(self, tasks, stagename="TASK"):
        """
        Process the build path and pass things to their respective handlers
        for further processing.
        """
        results = []
        cycle_start = time.time()

        for i, stage in enumerate(tasks):

            results[:] = []
            for parts in stage:
                try:
                    handler = self.task(parts[0])
                    if self.bot.api.player and \
                        handler.__class__ in self.bot.api.player.disable_modules:
                        continue
                    args = next(iter(parts[1:2]), ())
                    kwargs = next(iter(parts[2:3]), {})
                    result = handler.run(cycle_start, *args, **kwargs)
                    results.append(result)
                except (IndexError, KeyError, TypeError), e:
                    logger.exception(e)

            if False in results:
                logger.debug('Not all parts of %s stage %d are complete' % (stagename, i+1))
                break
