import logging
import random
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
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode


import emross
from emross.api import agent, Headers, read_body
from emross.exceptions import EmrossWarApiException
from emross.handlers import handlers, HTTP_handlers

from emross.api.cache import EmrossCache

logger = logging.getLogger(__name__)


class DummyResponse(object):
    def __init__(self, code, data):
        self.headers = None
        self.code = code
        self.data = data

class EmrossWarApi(object):
    USER_AGENT = """Mozilla/5.0 (iPhone; U; CPU iPhone OS 4_3_2 like Mac OS X; en-us) AppleWebKit/533.17.9 (KHTML, like Gecko) Mobile/8H7"""
    DEFAULT_HEADERS = {}

    def __init__(self, api_key, game_server, user_agent=None, pushid=None, player=None):
        self.api_key = api_key
        self.game_server = game_server
        self.user_agent = user_agent or self.USER_AGENT
        self.pushid = pushid
        self.player = player
        self.errors = []
        self.error_timer = 0
        self.shutdown = False
        self._headers = self.DEFAULT_HEADERS.copy()
        self._headers.update({
            'User-Agent': [self.user_agent]
        })
        self.headers = Headers(self._headers)

    @emross.defer.inlineCallbacks
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
                json = yield emross.defer.maybeDeferred(self._call, *args, **kwargs)

                if json['code'] in _handlers:
                    handler = _handlers[json['code']](self.bot, *args, **kwargs)
                    result = yield handler.process(json)
                    if result is not None:
                        emross.defer.returnValue(result)
                    # Try the current _call again
                    continue

                if not isinstance(json['code'], int):
                    logger.debug('API call attempt %d failed with an invalid client code.', i)
                    logger.warning(json)
                    yield emross.deferred_sleep(random.randrange(2,3))
                else:
                    emross.defer.returnValue(json)
            except EmrossWarApiException as e:
                logger.debug((args, kwargs))
                logger.debug(e)
                wait = 1 + (i % 10)
                logger.debug('Wait %d seconds before retry', wait)
                yield emross.deferred_sleep(wait)
            except (AttributeError, IndexError, JSONDecodeError) as e:
                logger.exception(e)
                logger.debug('Pause for a second.')
                yield emross.deferred_sleep(1)



    @emross.defer.inlineCallbacks
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
            emross.defer.returnValue({'code': EmrossWar.ERROR_INVALID_KEY, 'ret':''})

        params = OrderedDict([('jsonpcallback', 'jsonp%d' % epoch), ('_', epoch + 3600),
                    ('key', key), ('_l', emross.lang), ('_p', emross.device)])

        params.update(kwargs)
        params = (OrderedDict([(k,v) for k,v in params.iteritems() if v is not None]))

        try:
            url = 'http://{0}/{1}?{2}'.format(server, method, urlencode(params))
            logger.debug('Request: %s', url)
            response = yield agent.request('GET',
                url,
                self.headers
            )
            body = yield read_body(response)
        except Exception as e:
            logger.exception(e)
            response = DummyResponse(code=503, data=e)
            body = None

        if response.code not in [200, 304]:
            logger.debug(body)

            if handle_errors:
                self.errors.append((response.code, body))

                # Local handlers updated with global ones
                handlers = HTTP_handlers.copy()
                handlers.update(http_handlers)
                handler = handlers.get(response.code)

                if handler:
                    h = handler(self.bot)
                    result = yield h.process(self.errors)
                    if result:
                        emross.defer.returnValue(result)

            raise EmrossWarApiException('Unacceptable HTTP status code {0} returned'.format(response.code))

        jsonp = body[ body.find('(')+1 : body.rfind(')')]

        try:
            json = simplejson.loads(jsonp)
            logger.debug(json)
        except Exception:
            logger.debug('Error with decoding response data to JSON: %s', body)
            raise

        try:
            if int(json.get('code', 0)) == 0:
                self.error_timer = 0
        except AttributeError:
            pass
        finally:
            self.errors[:] = []

        wait = emross.ENFORCED_MINIMUM_DELAY
        if sleep is False:
            pass
        elif isinstance(sleep, float):
            wait += sleep
        elif sleep and isinstance(sleep, tuple):
            wait += random.randrange(*sleep)
        else:
            wait += random.random()

        if wait:
            logger.debug('Wait for %f seconds', wait)
            yield emross.deferred_sleep(wait)

        emross.defer.returnValue(json)


class URLHelper(object):

    def __init__(self, url, default='/', *args, **kwargs):
        self.url = url
        self.default = default
        self.args = args
        self.kwargs = kwargs

    def __str__(self):
        try:
            url = self.url(*self.args, **self.kwargs)
        except TypeError as e:
            logger.debug(e)
            url = self.url

        if url:
            return url

        try:
            # Is the default value calculated dynamically?
            return self.default()
        except TypeError:
            return self.default


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

    @classmethod
    def URL(cls, *args, **kwargs):
        logger.debug('Creating new URLHelper with args={0}, kwargs={1}'.format(args, kwargs))
        return URLHelper(*args, **kwargs)

# Dynamic properties
EmrossWar.MASTER_HOST = EmrossWar.URL(lambda: EmrossWar.CONFIG.get('MASTERHOST', '')[7:-1], lambda: emross.master)
EmrossWar.MASTER_QUERY_URL = EmrossWar.URL(lambda: EmrossWar.CONFIG.get('MASTER_QUERY_URL'), 'info.php')


if __name__ == "__main__":
    import emross
    print(emross.lang)

