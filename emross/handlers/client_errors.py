import handler
import logging
logger = logging.getLogger(__name__)


class InvalidKeyHandler(handler.EmrossHandler):
    def process(self, json):
        logger.warning('Invalid API key. Begin shutdown of this bot.')
        self.bot.disconnect()


class PvPEliminationHandler(handler.EmrossHandler):
    def process(self, json):
        logger.warning('You have been eliminated from PvP!')
        self.bot.disconnect()