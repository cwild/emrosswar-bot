import handler
import logging
import time

from emross import exceptions

logger = logging.getLogger(__name__)

class CoolDownHandler(handler.EmrossHandler):
    DELAY = 10

    def process(self, json):
        logger.debug('Wait {0} seconds for cooldown'.format(self.DELAY))
        time.sleep(self.DELAY)

class InvalidKeyHandler(handler.EmrossHandler):
    def process(self, json=None):
        logger.warning('Invalid API key!')
        logger.debug('Push an error handler onto the stack')
        args = (self.bot, self.bot.api.player.key)+self.args
        self.bot.errors.put((self.bot.api.player.update_api_key, args, self.kwargs))
        logger.debug('Wait until errors are cleared')
        self.bot.errors.join()
        logger.debug('Finished handling InvalidKey exception')


class PvPEliminationHandler(handler.EmrossHandler):
    def process(self, json):
        logger.warning('You have been eliminated from PvP!')
        self.bot.disconnect()

class VisitTooOftenHandler(handler.EmrossHandler):
    def process(self, json):
        raise exceptions.EmrossWarApiException('We have been rate limited. Come back later.')

class DevilArmyGone(handler.EmrossHandler):
    def process(self, json):
        raise exceptions.TargetException('Targeted NPC is gone!')

class DevilArmyAttackedTooOften(handler.EmrossHandler):
    def process(self, json):
        raise exceptions.TargetException('Targeted NPC has been attacked too often in last 24 hours!')
