import sys
sys.path.extend(['lib/urllib3/'])

import logging
import random
import simplejson
import time

from lib.ordered_dict import OrderedDict

from emross.exceptions import EmrossWarApiException
from urllib3 import HTTPConnectionPool, make_headers, exceptions

logger = logging.getLogger(__name__)

class EmrossWarApi:
    def __init__(self, api_key, game_server, user_agent):
        self.api_key = api_key
        self.game_server = game_server
        self.user_agent = user_agent

        self.pool = {}


    def call(self, method, server=None, sleep=(), **kargs):
        """Call API and return result"""
        server = server or self.game_server

        try:
            pool = self.pool[server]
        except KeyError:
            self.pool[server] = pool = HTTPConnectionPool(server, headers=make_headers(
                user_agent=self.user_agent, keep_alive=True, accept_encoding=True))


        epoch = int(time.time())
        params = OrderedDict([('jsonpcallback', 'jsonp%d' % epoch), ('_', epoch + 3600),
                    ('key', self.api_key)])

        params.update(kargs)
        params = (OrderedDict([(k,v) for k,v in params.iteritems() if v is not None]))

        try:
            url = 'http://%s/%s' % (server, method)
            r = pool.request('GET', url, fields=params)
        except exceptions.HTTPError, e :
            logger.exception(e)
            raise EmrossWarApiException, 'Problem connecting to game server.'

        jsonp = r.data
        jsonp = jsonp[ jsonp.find('(')+1 : jsonp.rfind(')')]

        try:
            json = simplejson.loads(jsonp)
            logger.debug(json)
        except ValueError, e:
            logger.exception(e)
            logger.debug(r.data)
            raise EmrossWarApiException, e

        if json['code'] == EmrossWar.ERROR_INVALID_KEY:
            print 'Invalid API key'
            exit()

        wait = random.random()
        if sleep:
            wait += random.randrange(*sleep)

        logger.debug('Wait for %f seconds' % wait)
        time.sleep(wait)

        return json



class EmrossWar:
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

    LORD = 1
    DEVIL_ARMY = 2
    COLONY = 3

    REACHED_HERO_LIMIT = 1304
    RECRUITING_CLOSED  = 1305
    INSUFFICIENT_GOLD  = 1306


    PVP_ELIMINATED = 7415
