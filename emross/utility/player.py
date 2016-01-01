import logging
import pickle

import emross
from emross.api import EmrossWar
from emross.exceptions import BotException, EmrossWarApiException
from emross.handlers.client_errors import BannedAccountHandler
from emross.utility.remote_api import RemoteApi
from emross.utility import settings

logger = logging.getLogger(__name__)


class Player(object):
    USER_CACHE = 'build/user.cache'
    LOGIN_URL = EmrossWar.URL(lambda: EmrossWar.CONFIG.get('FUNC_LOGIN'), 'game/login_api.php')

    def __init__(self,
        server,
        key=None,
        username=None,
        password=None,
        custom_build = None,
        disable_global_build = False,
        disable_modules = [],
        *args,
        **kwargs):

        self.server = server
        self.key = key
        self.username = username
        self.password = password

        self.custom_build = custom_build
        self.disable_global_build = disable_global_build
        self.disable_modules = set(disable_modules)
        self.playtimes = [(-1, 25)]
        self._remote = None

        self.ban_check = 0

        # Magic to update dict with whatever kwargs we receive
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

    def get(self, name, default=None):
        return self.__dict__.get(name, default)

    def __getattr__(self, name):
        return self.get(name)

    def __repr__(self):
        parts = []

        if self.username:
            parts.append('username={0}'.format(self.username))

        if not parts and self.key:
            parts.append('key={0}'.format(self.key))

        parts = ', '.join(parts)

        return '{0} ({1})'.format(self.__class__.__name__, parts)

    @property
    def remote(self):
        if not self._remote:
            try:
                self._remote = AccountApi(**settings.plugin_api)
            except AttributeError as e:
                logger.exception(e)

        return self._remote

    @emross.defer.inlineCallbacks
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


        json = yield api.call(EmrossWar.MASTER_QUERY_URL, server=EmrossWar.MASTER_HOST, user=self.username,
                    action='login', pvp=0, key=None, handle_errors=False, _handlers={14: BannedAccountHandler})

        if json['code'] != EmrossWar.SUCCESS:
            try:
                err = EmrossWar.LANG['ERROR']['SERVER'][str(json['code'])]
            except KeyError:
                err = gettext('Received error {0} during login').format(json['code'])

            msg = '"{0}": {1}'.format(self.username, err)
            yield bot.pushover.send_message(msg, title=gettext('Account Logon Error'))

            raise BotException(msg)

        server = json['ret']['server'][7:-1]
        user = json['ret']['user']

        json = yield api.call(self.LOGIN_URL, server=server, username=user, \
                    password=self.password, key=None, handle_errors=False)
        if json['code'] != EmrossWar.SUCCESS:
            raise BotException(EmrossWar.LANG['ERROR']['SERVER'].get(str(json['code']), gettext('Account login error')))

        # Reset the ban check
        self.ban_check = 0

        key = json['ret']['key']

        yield self._sync_pvp_key(bot, key, user, server)

        emross.defer.returnValue(key)

    @emross.defer.inlineCallbacks
    def update_api_key(self, bot, current_key, *args, **kwargs):
        """Try to find a new key for this bot to use. Search local cache,
        external API and then fallback to logging in directly"""

        logger.info('Try to acquire a valid API key for this account')

        try:
            cache = yield self.load_user_cache()
            key = cache[self.username]
            if key == current_key:
                logger.debug('Cached key matches current one, cannot use')
                del cache[self.username]
                self.save_user_cache(cache)
            else:
                logger.info('Found another key to use from "{0}"'.format(self.USER_CACHE))
                self.key = key
                emross.defer.returnValue(True)
        except IOError:
            logger.debug('Unable to load "{0}"'.format(self.USER_CACHE))
        except KeyError:
            logger.debug('No cached key for this account')

        # Check external API for a remotely cached key
        key, server = yield self.check_external_api(bot, invalid_key=current_key)
        if key and key != current_key:
            logger.info('We have another key to try from the remote API.')
            self.key = key
            self.update_user_cache(self.username, key)
            yield self._sync_pvp_key(bot, key, self.username, server)
            emross.defer.returnValue(True)

        # Last resort... login directly!
        try:
            key = yield self.account_login(bot, *args, **kwargs)
        except Exception as e:
            logger.info('Error encountered trying to acquire new key via login')
            if not self.key:
                raise e

            logger.info('Try current key to check if it really is stale')
            try:
                # Low level api._call to prevent using emross.handlers
                json = yield bot.api._call(bot.USERINFO_URL, handle_errors=False)
                if json['code'] == EmrossWar.SUCCESS:
                    self.key = current_key
                    emross.defer.returnValue(True)
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
            yield self.remote.sync_account(self.username, key, master=emross.master)


    @emross.defer.inlineCallbacks
    def check_external_api(self, bot=None, **kwargs):
        result = (None, None)

        if self.username is None:
            logger.debug('Unknown account username, unable to check')

        elif self.remote:
            data = yield self.remote.check_account(self.username, **kwargs)
            result = data.get('key'), (data.get('server') or '')[7:-1]

        emross.defer.returnValue(result)

    def load_user_cache(self):
        keys = {}
        try:
            with open(self.USER_CACHE, 'rb') as fp:
                keys = pickle.load(fp)
        except IOError:
            logger.debug('Unable to load "%s"', self.USER_CACHE)

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

    @emross.defer.inlineCallbacks
    def _sync_pvp_key(self, bot, key, user=None, server=None, **kwargs):
        if not bot.pvp:
            emross.defer.returnValue(None)

        json = yield bot.api._call(self.LOGIN_URL, sleep=False, handle_errors=False,
                            key=None, user=user, action='synckey', **kwargs)

        """
        Character not known in normal PvP world
        Try to sync with the World War server.
        Provide hero_id as 0. This is acceptable if a hero has manually
        been chosen already; otherwise, receive code 4005 and quit out!
        """
        if json['code'] == 12:
            json = yield bot.api._call('game/api_ww.php',
                server=server, key=key, action='switch', hero_id=0,
                sleep=False, handle_errors=False,
                **kwargs
            )
            if json['code'] == 4005:
                raise BotException('Manual hero selection required for World War!')

class AccountApi(RemoteApi):
    """Interact with an external API to get and synchronise """

    @emross.defer.inlineCallbacks
    def check_account(self, username, **kwargs):
        json = yield self.call('account/check', username=username, **kwargs)
        emross.defer.returnValue(json)

    @emross.defer.inlineCallbacks
    def sync_account(self, username, key, **kwargs):
        json = yield self.call('account/sync', username=username, key=key, **kwargs)
        emross.defer.returnValue(json)
