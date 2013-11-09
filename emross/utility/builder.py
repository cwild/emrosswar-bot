import threading
import time

from emross.utility.base import EmrossBaseObject


class BuildManager(EmrossBaseObject):

    def __init__(self, bot, *args, **kwargs):
        super(BuildManager, self).__init__(bot, *args, **kwargs)
        self.tasks = {}
        self.lock = threading.Lock()
        self.rlock = threading.RLock()
        self.running_build_stages = set()

    def task(self, task_class):
        with self.rlock:
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
        with self.lock:
            if stagename in self.running_build_stages:
                # This particular stagename is being run somewhere else
                return
            else:
                self.running_build_stages.add(stagename)

        results = []
        cycle_start = time.time()

        for i, stage in enumerate(tasks, start=1):

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
                self.log.debug('Not all parts of {0} stage {1} are complete'.format(stagename, i))
                break

        # Free this stage for other threads
        self.running_build_stages.remove(stagename)
