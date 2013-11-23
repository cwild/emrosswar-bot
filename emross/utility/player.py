import pickle
import settings

from emross import master as MASTER
from emross.api import EmrossWar
from emross.exceptions import BotException, EmrossWarApiException
from emross.utility.remote_api import RemoteApi

import logging
logger = logging.getLogger(__name__)


class Player(object):
    USER_CACHE = 'build/user.cache'
    LOGIN_URL = 'game/login_api.php'

    def __init__(self,
        server,
        key=None,
        pushid=None,
        user_agent=None,
        username=None,
        password=None,
        custom_build = None,
        disable_global_build = False,
        disable_modules = [],
        minimum_food=0,
        operators=[],
        *args,
        **kwargs):

        self.server = server
        self.key = key
        self.pushid = pushid
        self.user_agent = user_agent
        self.username = username
        self.password = password
        self.custom_build = custom_build
        self.disable_global_build = disable_global_build
        self.disable_modules = set(disable_modules)
        self.minimum_food = minimum_food
        self.operators = operators
        self._remote = None

    def __repr__(self):
        parts = []

        if self.username:
            parts.append('username={0}'.format(self.username))

        if not parts and self.key:
            parts.append('key={0}'.format(self.key))

        parts = ', '.join(parts)

        return 'Player ({0})'.format(parts)

    @property
    def remote(self):
        try:
            if self._remote:
                return self._remote

            remote = self._remote = AccountApi(**settings.plugin_api)
            return remote
        except AttributeError as e:
            logger.exception(e)
            return None

    def account_login(self, bot, *args, **kwargs):
        """Account login to acquire a new API key"""


        """
        m.emrosswar.com/info.php user=myuser action-login pvp=0
        {"code":0,"ret":{"server":"http://s123456.emrosswar.com\/","user":"myuser","referer":"myref","refercode":"myuser"}}

        ^^server game/login_api.php username=myuser password=mypass
        {"code":301,"ret":""} or {"code":0,"ret":{"key":"apikey..."}}
        """
        api = bot.api

        if not self.username:
            raise BotException('Account username must be set to relog with {0}'.format(api.player))

        if not self.password:
            raise EmrossWarApiException('No password set to relog with {}, try again soon'.format(api.player))


        json = api.call('info.php', server=MASTER, user=self.username,
                    action='login', pvp=0, key=None, handle_errors=False)

        if json['code'] != EmrossWar.SUCCESS:
            raise BotException('Invalid account username')

        server = json['ret']['server'][7:-1]
        user = json['ret']['user']

        json = api.call(self.LOGIN_URL, server=server, username=user, \
                    password=self.password, key=None, handle_errors=False)
        if json['code'] != EmrossWar.SUCCESS:
            raise BotException('Account password is incorrect')

        key = json['ret']['key']

        if bot.pvp:
            self._sync_pvp_key(bot, server, key, user)

        return key

    def update_api_key(self, bot, current_key, *args, **kwargs):
        """Try to find a new key for this bot to use. Search local cache,
        external API and then fallback to logging in directly"""

        logger.info('Try to acquire a valid API key for this account')
        try:
            cache = self.load_user_cache()
            key = cache[self.username]
            if key == current_key:
                logger.debug('Cached key matches current one, cannot use')
                del cache[self.username]
                self.save_user_cache(cache)
            else:
                logger.info('Found another key to use from "{0}"'.format(self.USER_CACHE))
                self.key = key
                bot.errors.task_done()
                return
        except IOError:
            logger.debug('Unable to load "{0}"'.format(self.USER_CACHE))
        except KeyError:
            logger.debug('No cached key for this account')

        # Check external API for a remotely cached key
        key = self.check_external_api(bot, invalid_key=current_key)
        if key and key != current_key:
            logger.info('We have another key to try from the remote API.')
            self.key = key
            self.update_user_cache(self.username, key)
            bot.errors.task_done()
            return

        # Last resort... login directly!
        try:
            key = self.account_login(bot, *args, **kwargs)
        except Exception as e:
            logger.info('Error encountered trying to acquire new key via login')
            if not self.key:
                raise e

            logger.info('Try current key to check if it really is stale')
            try:
                # Low level api._call to prevent using emross.handlers
                json = bot.api._call(bot.USERINFO_URL, handle_errors=False)
                if json['code'] == EmrossWar.SUCCESS:
                    self.key = current_key
                    bot.errors.task_done()
                    return
            except Exception:
                pass

            # Current key didn't work out, pass the exception
            raise e

        if self.username:
            self.update_user_cache(self.username, key)
        self.key = key

        # Sync the key with our external API
        if self.remote:
            logger.debug('Push new key to remote API for account "{0}"'.format(self.username))
            self.remote.sync_account(self.username, key, master=MASTER)

        bot.errors.task_done()


    def check_external_api(self, bot=None, **kwargs):
        if self.username is None:
            logger.debug('Unknown account username, unable to check')
            return

        if self.remote:
            data = self.remote.check_account(self.username, **kwargs)
            key = data.get('key', None)
            game_world = data.get('server')

            if bot.pvp and game_world:
                self._sync_pvp_key(bot, game_world[7:-1], key, user=data.get('user'))

            return key

    def load_user_cache(self):
        keys = {}
        try:
            with open(self.USER_CACHE, 'rb') as fp:
                keys = pickle.load(fp)
        except IOError:
            logger.debug('Unable to load "%s"' % self.USER_CACHE)

        return keys

    def save_user_cache(self, keys):
        try:
            with open(self.USER_CACHE, 'wb') as fp:
                pickle.dump(keys, fp)
        except IOError as e:
            logger.exception(e)

    def update_user_cache(self, username, key):
        cache = self.load_user_cache()
        cache[username] = key
        self.save_user_cache(cache)

    def _sync_pvp_key(self, bot, game_world, key, user=None,  **kwargs):
        json = bot.api.call(self.LOGIN_URL, server=game_world, sleep=False,
                            key=key, user=user, action='synckey')

        """
        Character not known in normal PvP world
        Try to sync with the World War server.
        Provide hero_id as 0. This is acceptable if a hero has manually
        been chosen already; otherwise, receive code 4005 and quit out!
        """
        if json['code'] == 12:
            json = bot.api.call('game/api_ww.php', server=game_world,
                sleep=False,
                key=key,
                action='switch',
                hero_id=0
            )
            if json['code'] == 4005:
                raise BotException('Manual hero selection required for World War!')

class AccountApi(RemoteApi):
    """Interact with an external API to get and synchronise """

    def check_account(self, username, **kwargs):
        return self.call('account/check', username=username, **kwargs)

    def sync_account(self, username, key, **kwargs):
        return self.call('account/sync', username=username, key=key, **kwargs)
