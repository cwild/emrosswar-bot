import hashlib
import logging
import random

import emross
from emross import exceptions
from emross.handlers import handler

logger = logging.getLogger(__name__)

class BannedAccountHandler(handler.EmrossHandler):
    BAN_CHECKS = 1

    def process(self, json, *args, **kwargs):
        try:
            if self.bot.api.player.ban_check >= self.BAN_CHECKS:
                self.log.warning(gettext('Banned. Nothing can be done!'))
                return json

            self.log.info(gettext('Account is banned! Check whether we can connect directly to the game server'))
            data = self.bot.api.player.remote.check_account(self.bot.api.player.username, banned=True)
            self.bot.api.player.ban_check += 1

            from emross.api import EmrossWar

            return {
                'code': EmrossWar.SUCCESS,
                'ret': {'server':data.get('server'), 'user':self.bot.api.player.username}
                }
        except Exception as e:
            self.log.error(e)


class CoolDownHandler(handler.EmrossHandler):
    DELAY = 10

    @emross.defer.inlineCallbacks
    def process(self, json):
        logger.debug('Wait {0} seconds for cooldown'.format(self.DELAY))
        yield emross.deferred_sleep(self.DELAY)

class InsufficientResources(handler.EmrossHandler):

    @emross.defer.inlineCallbacks
    def process(self, json=None):
        try:
            city = int(self.kwargs['city'])
            for c in self.bot.cities:
                if c.id == city:
                    c.expire()
                    break
        except KeyError:
            for c in self.bot.cities:
                c.expire()

        # Don't wish to hold anything else up
        emross.defer.returnValue(json)

class InvalidDataHandler(handler.EmrossHandler):
    DELAY = 30

    @emross.defer.inlineCallbacks
    def process(self, json):
        self.log.info(gettext('Invalid data, try again after {0}s').format(self.DELAY))
        self.log.debug((self.args, self.kwargs))

        yield emross.deferred_sleep(self.DELAY)

class InvalidKeyHandler(handler.EmrossHandler):

    @emross.defer.inlineCallbacks
    def process(self, json=None):
        logger.warning(gettext('Invalid API key!'))

        logger.debug(gettext('Setup an error handler and wait on it'))
        args = (self.bot, self.bot.api.player.key)+self.args

        self.bot.error = self.bot.api.player.update_api_key(*args, **self.kwargs)
        solved = yield self.bot.error

        if solved:
            # No longer in an error state
            self.bot.error = None

        logger.debug(gettext('Finished handling InvalidKey exception'))


class PlayerRaceSelection(handler.EmrossHandler):
    AUTOMATIC = False

    def process(self, json):
        self.log.warning('No player race has been selected!')
        result = {}

        def race_selection(result, *args, **kwargs):
            if self.AUTOMATIC:
                try:
                    # Ordinal value of first char of username hash
                    race = 1 + ord(hashlib.sha1(self.bot.api.player.username).hexdigext()[0])
                except AttributeError:
                    race = random.randint(1, 3)
                self.log.debug('Selected race: {0}'.format(race))

                _json = self.bot.api.call('game/init/create_role_api.php', txtrolename='', txtcityname='', country=race)
                # Did we get an EmrossWar.SUCCESS code?
                if _json['code'] == 0:
                    result.update(_json)
                self.bot.errors.task_done()
            else:
                self.bot.disconnect()
                raise exceptions.BotException('Cannot continue without a chosen race')

        self.bot.errors.put((race_selection, (result,)+self.args, self.kwargs))
        self.bot.errors.join()
        return result

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

class CaptchaHandler(handler.EmrossHandler):
    DELAY_PERIOD = 1800

    def process(self, json):
        raise exceptions.DelayTaskProcessing('Try this Task again later!', self.DELAY_PERIOD)
