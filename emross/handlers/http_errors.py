import logging

import emross
from emross.handlers.handler import EmrossHandler
from emross.handlers.client_errors import InvalidKeyHandler

logger = logging.getLogger(__name__)


class ServiceUnavailableHandler(EmrossHandler):
    HTTP_STATUS_CODE = 503
    RETRIES = 3
    DELAY = 30

    @emross.defer.inlineCallbacks
    def process(self, errors):
        count = len([status for status, data in errors if status == self.HTTP_STATUS_CODE])

        if count < self.RETRIES:
            logger.debug('Error may be temporary (current count %d)', count)
            yield emross.deferred_sleep(self.DELAY)
        else:
            logger.debug('We keep seeing HTTP error %d; try relogging to clear it', self.HTTP_STATUS_CODE)

            # Just reuse the invalid key handler
            handler = InvalidKeyHandler(self.bot)
            result = yield handler.process()
            emross.defer.returnValue(result)
