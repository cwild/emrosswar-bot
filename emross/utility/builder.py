import logging
logger = logging.getLogger(__name__)

import time

class BuildManager(object):

    def __init__(self, bot, path=None, *args, **kwargs):
        self.bot = bot
        self.path = path
        self.tasks = {}
        super(BuildManager, self).__init__(*args, **kwargs)

    def process(self):
        """
        Process the build path and pass things to their respective handlers
        for further processing.
        """
        results = []
        cycle_start = time.time()

        for i, stage in enumerate(self.path):
            logger.debug('Processing build stage %d' % i)

            results[:] = []
            for parts in stage:
                try:
                    cls = parts[0]
                    handler = self.tasks[cls]
                except KeyError, e:
                    handler = self.tasks[cls] = cls(self.bot)
                except TypeError, e:
                    logger.exception(e)
                    continue


                try:
                    args = next(iter(parts[1:2]), ())
                    kwargs = next(iter(parts[2:3]), {})
                    result = handler.run(cycle_start, *args, **kwargs)
                    results.append(result)
                except (IndexError, KeyError), e:
                    logger.exception(e)

            if False in results:
                logger.debug('Not all parts of stage %d are complete' % (i+1))
                break
