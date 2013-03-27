import logging
logger = logging.getLogger(__name__)

from emross.exceptions import EmrossWarException
from emross.handlers.handler import EmrossHandler
from emross.handlers.client_errors import InvalidKeyHandler


class ServiceUnavailableHandler(EmrossHandler):
    HTTP_STATUS_CODE = 503

    def process(self, errors):
        count = len([status for status, data in errors if status == self.HTTP_STATUS_CODE])

        if count < 3:
            logger.debug('Error may be temporary (current count %d)' % count)
        else:
            logger.debug('We keep seeing HTTP error %d; try relogging to clear it' % self.HTTP_STATUS_CODE)

            # Just reuse the invalid key handler
            handler = InvalidKeyHandler(self.bot, error_exception=EmrossWarException)
            handler.process()
