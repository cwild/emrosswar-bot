import logging
import random
import sys
import threading
import time

import simplejson
try:
    from simplejson import JSONDecodeError
except ImportError:
    class JSONDecodeError(ValueError): pass

from lib.ordered_dict import OrderedDict

sys.path.extend(['lib/urllib3/'])
from urllib3 import PoolManager, make_headers, exceptions


from emross import device, lang
from emross.exceptions import EmrossWarApiException
from emross.handlers import handlers, HTTP_handlers

from emross.api.cache import EmrossCache

logger = logging.getLogger(__name__)

class EmrossWarApi(object):
    _LOCK = threading.Lock()
    CONN_POOL = None
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

    @classmethod
    def init_pool(cls, connections=10, timeout=15, **kwargs):
        with cls._LOCK:
            if cls.CONN_POOL is None:
                cls.CONN_POOL = PoolManager(maxsize=connections, timeout=timeout, **kwargs)
                logger.info('PoolManager initialised with {0} connections'.format(connections))

    @property
    def pool(self):
        pool = self.__class__.CONN_POOL
        if not pool:
            self.__class__.init_pool()
            pool = self.__class__.CONN_POOL
        return pool

    def create_headers(self):
        return make_headers(user_agent=self.user_agent, keep_alive=True, accept_encoding=True)

    def call(self, *args, **kargs):
        for i in xrange(1, 6):
            try:
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
        handle_errors=True,
        **kargs):
        """Call API and return result"""
        server = server or self.game_server

        epoch = int(time.time())

        try:
            key = self.player.key
        except AttributeError:
            key = self.api_key

        if handle_errors and (key is None or key.strip() == '') and 'key' not in kargs:
            logger.debug('API key is missing, send dummy InvalidKey error')
            return {'code': EmrossWar.ERROR_INVALID_KEY, 'ret':''}

        params = OrderedDict([('jsonpcallback', 'jsonp%d' % epoch), ('_', epoch + 3600),
                    ('key', key), ('_l', lang), ('_p', device)])

        params.update(kargs)
        params = (OrderedDict([(k,v) for k,v in params.iteritems() if v is not None]))

        try:
            r = self.pool.request(
                    'GET',
                    'http://{0}/{1}'.format(server, method),
                    fields=params, headers=self.create_headers()
                )
        except exceptions.HTTPError as e:
            logger.exception(e)

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

        jsonp = r.data
        jsonp = jsonp[ jsonp.find('(')+1 : jsonp.rfind(')')]

        json = simplejson.loads(jsonp)
        logger.debug(json)

        if int(json.get('code', 0)) == 0:
            self.error_timer = 0
        self.errors[:] = []

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

    REACHED_HERO_LIMIT = 1304
    RECRUITING_CLOSED  = 1305
    INSUFFICIENT_GOLD  = 1306
    ITEM_DOES_NOT_EXIST = 3403

    PVP_ELIMINATED = 7415

    @staticmethod
    def safe_text(s):
        if isinstance(s, unicode):
            return s.encode('utf-8')
        elif isinstance(s, str):
            # Must be encoded in UTF-8
            return s.decode('utf-8')
        return s

if __name__ == "__main__":
    import emross
    print emross.lang

