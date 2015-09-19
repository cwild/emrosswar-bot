import logging
import random
import sys
import threading
import time
from lib import six

try:
    import simplejson
except ImportError:
    import json as simplejson

try:
    from simplejson import JSONDecodeError
except ImportError:
    class JSONDecodeError(ValueError): pass

try:
    from collections import OrderedDict
except ImportError:
    from lib.ordered_dict import OrderedDict


try:
    # Natively installed version
    import urllib3
except ImportError:
    sys.path.extend(['lib/urllib3/'])
    import urllib3


from emross import device, lang
from emross.exceptions import EmrossWarApiException
from emross.handlers import handlers, HTTP_handlers

from emross.api.cache import EmrossCache

logger = logging.getLogger(__name__)


class DummyResponse(object):
    def __init__(self, status, data):
        self.headers = None
        self.status = status
        self.data = data

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
        self.shutdown = False
        self._headers = urllib3.make_headers(\
            user_agent=self.user_agent,
            keep_alive=True,
            accept_encoding=True
        )

    @classmethod
    def init_pool(cls, connections=10, timeout=15, **kwargs):
        with cls._LOCK:
            if cls.CONN_POOL is None:
                cls.CONN_POOL = urllib3.PoolManager(maxsize=connections, timeout=timeout, **kwargs)
                logger.debug('PoolManager initialised with {0} connections'.format(connections))

    @property
    def pool(self):
        if not self.CONN_POOL:
            self.init_pool()

        return self.CONN_POOL

    def call(self, *args, **kwargs):

        try:
            _handlers = handlers.copy()
            _handlers.update(kwargs['_handlers'])
            del kwargs['_handlers']
        except (KeyError, TypeError):
            pass

        for i in six.moves.range(1, 6):
            if self.shutdown:
                raise EmrossWarApiException('No further API calls permitted for {0}'.format(self.player))
            try:
                json = self._call(*args, **kwargs)

                if json['code'] in _handlers:
                    handler = _handlers[json['code']](self.bot, *args, **kwargs)
                    result = handler.process(json)
                    if result is not None:
                        return result
                    # Try the current _call again
                    continue

                if not isinstance(json['code'], int):
                    logger.debug('API call attempt %d failed with an invalid client code.', i)
                    logger.warning(json)
                    time.sleep(random.randrange(2,3))
                else:
                    return json
            except (AttributeError, EmrossWarApiException, IndexError, JSONDecodeError) as e:
                logger.exception(e)
                logger.debug('Pause for a second.')
                time.sleep(1)
            except urllib3.exceptions.HTTPError as e:
                logger.debug((args, kwargs))
                logger.debug(e)
                wait = 1 + (i % 10)
                logger.debug('Wait %d seconds before retry', wait)
                time.sleep(wait)


    def _call(self, method, server=None,
        sleep=(),
        handle_errors=True,
        http_handlers={},
        **kwargs):
        """Call API and return result"""
        server = server or self.game_server

        epoch = int(time.time())

        try:
            key = self.player.key
        except AttributeError:
            key = self.api_key

        if handle_errors and (key is None or key.strip() == '') and 'key' not in kwargs:
            logger.debug('API key is missing, send dummy InvalidKey error')
            return {'code': EmrossWar.ERROR_INVALID_KEY, 'ret':''}

        params = OrderedDict([('jsonpcallback', 'jsonp%d' % epoch), ('_', epoch + 3600),
                    ('key', key), ('_l', lang), ('_p', device)])

        params.update(kwargs)
        params = (OrderedDict([(k,v) for k,v in params.iteritems() if v is not None]))

        try:
            r = self.pool.request(
                    'GET',
                    'http://{0}/{1}'.format(server, method),
                    fields=params, headers=self._headers
                )
        except urllib3.exceptions.HTTPError as e:
            logger.exception(e)
            r = DummyResponse(status=503, data=e)

        if r.status not in [200, 304]:
            logger.debug(r.data)

            if handle_errors:
                self.errors.append((r.status, r.data))

                # Local handlers updated with global ones
                handlers = HTTP_handlers.copy()
                handlers.update(http_handlers)
                handler = handlers.get(r.status)

                if handler:
                    h = handler(self.bot)
                    result = h.process(self.errors)
                    if result:
                        return result

            raise urllib3.exceptions.HTTPError('Unacceptable HTTP status code %d returned' % r.status)

        jsonp = r.data
        jsonp = jsonp[ jsonp.find('(')+1 : jsonp.rfind(')')]

        try:
            json = simplejson.loads(jsonp)
            logger.debug(json)
        except Exception:
            logger.debug('Error with response. Headers: {0}, Body: {1}'.format(r.headers, r.data))
            raise

        try:
            if int(json.get('code', 0)) == 0:
                self.error_timer = 0
        except AttributeError:
            pass
        finally:
            self.errors[:] = []

        if sleep is False:
            # No delay from our end
            pass
        else:
            wait = random.random()
            if sleep:
                wait += random.randrange(*sleep)

                logger.debug('Wait for %f seconds', wait)
                time.sleep(wait)

        return json



class EmrossWar(six.with_metaclass(EmrossCache)):

    SUCCESS = 0
    ERROR_UNKNOWN = -1
    ERROR_INVALID_KEY = 2

    TRUCE = 1
    VACATION = 2
    SLEEP = 4

    REACHED_HERO_LIMIT = 1304
    RECRUITING_CLOSED  = 1305
    INSUFFICIENT_GOLD  = 1306
    ITEM_DOES_NOT_EXIST = 3403

    INVALID_DATA = 2513

    @staticmethod
    def safe_text(s):
        return s if isinstance(s, unicode) else six.u(s)

if __name__ == "__main__":
    import emross
    print(emross.lang)

