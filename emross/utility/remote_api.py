import logging
logger = logging.getLogger(__name__)

import json

import sys
sys.path.extend(['lib/urllib3/'])

import urllib3
import urlparse

__version__ = '1.0.0'
USER_AGENT = 'com.cryformercy.emross.emrosswar-bot %s' % __version__

class RemoteApiException(urllib3.exceptions.HTTPError): pass

class RemoteApi(object):
    pool = urllib3.PoolManager()

    def __init__(self, url, auth, *args, **kwargs):
        super(RemoteApi, self).__init__(*args, **kwargs)

        self.url = url
        self.headers = urllib3.util.make_headers(basic_auth = auth, \
            keep_alive=True, accept_encoding=True, user_agent = USER_AGENT)

    def call(self, uri, method='POST', decoder=json.loads, *args, **kwargs):
        url = urlparse.urljoin(self.url, uri)
        r = self.__class__.pool.request(method, url, fields=kwargs, headers=self.headers)
        if r.status is 401:
            raise RemoteApiException, 'Incorrect login details'

        try:
            return decoder(r.data)
        except ValueError:
            raise RemoteApiException, 'Problem decoding data: %s' % r.data


if __name__ == "__main__":
    import settings
    logging.basicConfig(level=logging.DEBUG)

    api = RemoteApi(**settings.plugin_api)
    print 'Server echo: ping => %s' % api.call('system/echo', message='ping')
    print 'Server time: %s' % api.call('system/time', 'GET')