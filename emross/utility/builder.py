from emross.research.studious import Study
from emross.structures.construction import Construct

import logging
logger = logging.getLogger(__name__)

class BuildManager(object):
    TASKS = (Study, Construct)

    def __init__(self, bot, path=None, *args, **kwargs):
        self.bot = bot
        self.path = path
        self.stage = 0

        self.tasks = {}
        for task in self.__class__.TASKS:
            t = task(self.bot)
            self.tasks[t.__class__] = t

        super(BuildManager, self).__init__(*args, **kwargs)

    def process(self):
        """
        Process the build path and pass things to their respective handlers
        for further processing.
        """
        results = []

        for i, stage in enumerate(self.path):
            logger.debug('Processing build stage %d' % i)

            results[:] = []
            for parts in stage:
                try:
                    handler = self.tasks[parts[0]]
                    args = next(iter(parts[1:2]), ())
                    kwargs = next(iter(parts[2:3]), {})
                    result = handler.process(*args, **kwargs)
                    results.append(result)
                except (IndexError, KeyError), e:
                    logger.exception(e)

            if False in results:
                logger.debug('Not all parts of stage %d are complete' % (i+1))
                break
