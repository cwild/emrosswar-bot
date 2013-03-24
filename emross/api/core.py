import sys
sys.path.extend(['lib/urllib3/'])

import logging
import random

import simplejson
try:
    from simplejson import JSONDecodeError
except ImportError:
    class JSONDecodeError(ValueError): pass

import threading
import time

from lib.ordered_dict import OrderedDict

from urllib3 import PoolManager, make_headers, exceptions

from emross.exceptions import EmrossWarApiException
from emross.handlers import handlers, HTTP_handlers

from emross.api.cache import EmrossCache

logger = logging.getLogger(__name__)

class EmrossWarApi(object):
    _pool = PoolManager(maxsize=10, timeout=15)
    USER_AGENT = """Mozilla/5.0 (iPhone; U; CPU iPhone OS 4_3_2 like Mac OS X; en-us) AppleWebKit/533.17.9 (KHTML, like Gecko) Mobile/8H7"""

    def __init__(self, api_key, game_server, user_agent=None, pushid=None, player=None):
        self.api_key = api_key
        self.game_server = game_server
        self.user_agent = user_agent or self.USER_AGENT
        self.pushid = pushid
        self.player = player
        self.errors = []
        self.error_timer = 0
        self.lock = threading.Lock()

    @property
    def pool(self):
        return self.__class__._pool

    def create_headers(self):
        return make_headers(user_agent=self.user_agent, keep_alive=True, accept_encoding=True)

    def call(self, *args, **kargs):
        for i in xrange(1, 6):
            try:
                logger.debug('API call: attempt #%d' % i)
                json = self._call(*args, **kargs)

                if json['code'] in handlers:
                    handler = handlers[json['code']](self.bot)
                    result = handler.process(json)
                    if result is not None:
                        return result
                    # Try the current _call again
                    continue

                if not isinstance(json['code'], int):
                    logger.debug('API call attempt %d failed with an invalid client code.' % i)
                    logger.warning(json)
                    time.sleep(random.randrange(2,3))
                else:
                    return json
            except (AttributeError, EmrossWarApiException, IndexError, JSONDecodeError) as e:
                logger.exception(e)
                logger.debug('Pause for a second.')
                time.sleep(1)
            except exceptions.HTTPError as e:
                logger.debug(e)
                wait = 1 + (i % 10)
                logger.info('Wait %d seconds before retry' % wait)
                time.sleep(wait)


    def _call(self, method, server=None,
        sleep=(),
        _lock=True,
        handle_errors=True,
        **kargs):
        """Call API and return result"""
        server = server or self.game_server

        from emross.api import device, lang
        epoch = int(time.time())

        try:
            key = self.player.key
        except AttributeError:
            key = self.api_key

        if (key is None or key.strip() == '') and 'key' not in kargs:
            logger.debug('API key is missing, send dummy InvalidKey error')
            return {'code': EmrossWar.ERROR_INVALID_KEY, 'ret':''}

        params = OrderedDict([('jsonpcallback', 'jsonp%d' % epoch), ('_', epoch + 3600),
                    ('key', key), ('_l', lang), ('_p', device)])

        params.update(kargs)
        params = (OrderedDict([(k,v) for k,v in params.iteritems() if v is not None]))

        try:
            url = 'http://%s/%s' % (server, method)
            if _lock:
                with self.lock:
                    r = self.pool.request('GET', url, fields=params, headers=self.create_headers())
            else:
                r = self.pool.request('GET', url, fields=params, headers=self.create_headers())
        except exceptions.HTTPError as e :
            logger.exception(e)
            #raise EmrossWarApiException('Problem connecting to game server.')

            class DummyResponse(object):
                pass

            r = DummyResponse()
            r.status = 503
            r.data = e



        if r.status not in [200, 304]:
            logger.debug(r.data)

            if handle_errors:
                self.errors.append((r.status, r.data))
                handler = HTTP_handlers.get(r.status, None)
                if handler:
                    h = handler(self.bot)
                    result = h.process(self.errors)
                    if result:
                        return result

            raise exceptions.HTTPError('Unacceptable HTTP status code %d returned' % r.status)
        else:
            self.error_timer = 0
            self.errors[:] = []

        jsonp = r.data
        jsonp = jsonp[ jsonp.find('(')+1 : jsonp.rfind(')')]

        json = simplejson.loads(jsonp)
        logger.debug(json)

        if sleep is False:
            # No delay from our end
            pass
        else:
            wait = random.random()
            if sleep:
                wait += random.randrange(*sleep)

                logger.debug('Wait for %f seconds' % wait)
                time.sleep(wait)

        return json



class EmrossWar(object):
    __metaclass__ = EmrossCache

    SUCCESS = 0
    ERROR_UNKNOWN = -1
    ERROR_INVALID_KEY = 2
    #ERROR_AUTHFAIL = {12:1, 14:1, 301:1, 302:1}


    """
    3: "Scout",
    0: "Loot",
    7: "Attack",
    8: "Occupy",
    9: "Conquer",
    5: "Build",
    2: "Transport"
    """
    ATTACK_TYPE_SCOUT = 3
    ACTION_ATTACK = 7

    TRUCE = 1
    VACATION = 2
    SLEEP = 4

    LORD = 1
    DEVIL_ARMY = 2
    COLONY = 3

    REACHED_HERO_LIMIT = 1304
    RECRUITING_CLOSED  = 1305
    INSUFFICIENT_GOLD  = 1306
    ITEM_DOES_NOT_EXIST = 3403

    PVP_ELIMINATED = 7415


if __name__ == "__main__":
    import emross.api
    print emross.api.lang

