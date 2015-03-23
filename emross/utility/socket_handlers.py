import logging
from multiprocessing.dummy import Process

try:
    import simplejson
except ImportError:
    import json as simplejson

import emross
from emross.utility.events import Event

from emross.utility import settings


logger = logging.getLogger(__name__)


class JsonSocketHandler(Process):

    def __init__(self, socket, bots):
        super(JsonSocketHandler, self).__init__()
        self.socket = socket
        self.bots = bots

        self.handlers = {
            401: self.auth_handler,
            10001: self.game_world_setter
        }

    def run(self, *args, **kwargs):
        logger.debug('Started {0} worker'.format(self.__class__.__name__))

        bots, queue = self.bots, self.socket.queue_in
        while True:
            try:
                data = queue.get()
                self.process(data)
            except Exception as e:
                logger.exception(e)


    def bot_finder(self, account):
        return (bot
            for bot in self.bots
            if account == 0 or account == bot.userinfo['id']
        )

    def process(self, data):
        """
        Do something with the data that we have received!
        """

        logger.debug(data)
        json = simplejson.loads(data)

        handler = self.handlers.get(int(json.get('code', 0)))

        if handler:
            res = handler(json)
            if res:
                payload = simplejson.dumps(res)
                self.socket.queue_out.put(payload)
        elif 'account' in json:
            account = int(json['account'])
            for bot in self.bot_finder(account):
                bot.events.notify(Event(json['event']), json['payload'])


    def auth_handler(self, json):
        logger.debug(json['message'])

        try:
            user, password = settings.plugin_api['auth'].split(':', 1)
        except Exception as e:
            logger.exception(e)

        return {'username': user, 'password': password}

    def game_world_setter(self, json):
        return {
            'method': 'game.master.set',
            'payload': {'master': emross.master}
        }
