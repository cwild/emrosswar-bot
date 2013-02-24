import handler
import logging
logger = logging.getLogger(__name__)

class InvalidKeyHandler(handler.EmrossHandler):
    def process(self, json=None):
        logger.warning('Invalid API key!')
        logger.debug('Push an error handler onto the stack')
        self.bot.errors.put((self.bot.api.player.update_api_key, (self.bot, self.bot.api.player.key)))
        logger.debug('Wait until errors are cleared')
        self.bot.errors.join()
        logger.debug('Finished handling InvalidKey exception')


class PvPEliminationHandler(handler.EmrossHandler):
    def process(self, json):
        logger.warning('You have been eliminated from PvP!')
        self.bot.disconnect()
