import json
import logging
import urllib
import urlparse

from base64 import b64encode
from twisted.web.iweb import IBodyProducer
from zope.interface import implements


import emross
from emross.api import agent, Headers, read_body

logger = logging.getLogger(__name__)

__version__ = '1.1.0'
USER_AGENT = 'com.cryformercy.emross.emrosswar-bot %s' % __version__

class POSTDataProducer(object):
    implements(IBodyProducer)

    def __init__(self, data_dict):
        self.body = urllib.urlencode(data_dict)
        self.length = len(self.body)
        logger.debug(self.body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        return emross.defer.succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass

class RemoteApiException(Exception): pass

class RemoteApi(object):

    def __init__(self, url, auth=None, *args, **kwargs):
        super(RemoteApi, self).__init__()

        self.url = url
        self.headers = {
            'User-Agent': [USER_AGENT]
        }
        try:
            self.headers['Authorization'] = ['Basic {0}'.format(b64encode(auth))]
        except TypeError:
            pass


    @emross.defer.inlineCallbacks
    def call(self, uri, method='POST', decoder=json.loads, *args, **kwargs):
        url = urlparse.urljoin(self.url, uri)
        logger.debug('Request: %s %s', method, url)
        kwargs = dict([(k, v) for k, v in kwargs.iteritems() if v is not None])

        headers = self.headers.copy()
        body = None

        if method == 'POST':
            headers['Content-Type'] = ['application/x-www-form-urlencoded']
            body = POSTDataProducer(kwargs)

        response = yield agent.request(method, url, Headers(headers), body)
        if response.code is 401:
            raise RemoteApiException('Incorrect login details')

        body = yield read_body(response)

        try:
            data = decoder(body)
            logger.debug(str(data))
            emross.defer.returnValue(data)
        except ValueError:
            raise RemoteApiException('Problem decoding data: {0}'.format(data))

    def json_decode(self, s):
        return json.loads(s)

    def json_encode(self, obj):
        return json.dumps(obj)

if __name__ == "__main__":
    import emross.utility.settings
    settings = emross.utility.settings.load('settings')
    logging.basicConfig(level=logging.DEBUG)

    api = RemoteApi(**settings.plugin_api)
    print 'Server echo: ping => %s' % api.call('system/echo', message='ping')
    print 'Server time: %s' % api.call('system/time', 'GET')
    print 'Socket discovery => {host}:{port}'.format(**api.call('socket/discover', testing=0))
