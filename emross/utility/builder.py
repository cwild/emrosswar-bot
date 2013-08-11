import threading
import time

from emross.utility.base import EmrossBaseObject


class BuildManager(EmrossBaseObject):

    def __init__(self, bot, *args, **kwargs):
        self.tasks = {}
        self.lock = threading.RLock()
        super(BuildManager, self).__init__(bot, *args, **kwargs)
        self.log.debug('Build manager init')

    def task(self, task_class):
        with self.lock:
            try:
                handler = self.tasks[task_class]
            except KeyError:
                handler = self.tasks[task_class] = task_class(self.bot)
            except TypeError as e:
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
                    result = handler.run(cycle_start, i, *args, **kwargs)
                    results.append(result)
                except Exception as e:
                    self.log.exception(e)

            if False in results:
                self.log.debug('Not all parts of {0} stage {1} are complete'.format(stagename, i+1))
                break
