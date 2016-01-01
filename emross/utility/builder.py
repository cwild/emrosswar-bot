import time

import emross
from emross.utility.base import EmrossBaseObject


class BuildManager(EmrossBaseObject):

    def __init__(self, bot, *args, **kwargs):
        super(BuildManager, self).__init__(bot, *args, **kwargs)
        self.tasks = {}
        self.running_build_stages = set()

    def task(self, task_class):
        """
        Maintain a single instance of a Task
        """
        if task_class not in self.tasks:
            try:
                self.tasks[task_class] = task_class(self.bot)
            except TypeError as e:
                logger.exception(e)
                raise e

        return self.tasks[task_class]

    @emross.defer.inlineCallbacks
    def process(self, tasks, stagename="TASK"):
        """
        Process the build path and pass things to their respective handlers
        for further processing.
        """

        results = []
        cycle_start = time.time()
        next_runtimes = []

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
                    result = yield handler.run(cycle_start, i, *args, **kwargs)
                    results.append(result)
                    next_runtimes.append(handler._next_run)
                except Exception as e:
                    self.log.exception(e)

            if False in results:
                #self.log.debug('Not all parts of {0} stage {1} are complete'.format(stagename, i))
                break

        # Free this stage for other threads
        self.running_build_stages.remove(stagename)
        emross.defer.returnValue(next_runtimes)

    @emross.defer.inlineCallbacks
    def run(self, tasks):
        """
        Kick off our task handlers
        """
        self.log.debug('Begin task scheduler with {0}'.format(tasks))
        wait_periods = []

        while not self.bot.closing:
            wait_periods[:] = []
            for task, jobs in tasks.iteritems():
                if task not in self.running_build_stages:
                    self.running_build_stages.add(task)
                    wait = yield self.process(jobs, task)
                    wait_periods.extend(wait)

            # Now wait until we need to run another task agin
            wait = min([t for t in wait_periods if t > 0]) - time.time()
            wait = max(wait, 0)
            self.log.debug('Run again in %f seconds', wait)
            yield emross.deferred_sleep(wait)