try:
    import cPickle as pickle
except ImportError, e:
    import pickle

import os
import logging
import urllib

logger = logging.getLogger(__name__)

class Session(object):
    PATH = 'build/session.{server}-{userid}.pickle'

    def __init__(self, bot):
        self.__dict__['bot'] = bot
        self.__dict__['data'] = set()
        self.__dict__['exists'] = None
        self.__dict__['loaded'] = False

    @property
    def filename(self):
        server = self.bot.api.game_server
        userid = self.bot._data.get('id') or self.bot.userinfo['id']
        filename = self.PATH.format(server=urllib.quote(server, safe=''), userid=userid)
        logger.debug(filename)
        return filename

    def __getattr__(self, name):
        self.load()
        return super(Session, self).__getattribute__(name)

    def __setattr__(self, name, value):
        super(Session, self).__setattr__(name, value)
        self.__dict__['data'].add(name)

    def __delattr__(self, name):
        super(Session, self).__delattr__(name)
        self.__dict__['data'].remove(name)

    def save(self):
        data = {}
        for name in self.__dict__['data']:
            val = getattr(self, name, None)
            if val:
                data[name] =  val

        try:
            with open(self.filename, 'wb') as fp:
                pickle.dump(data, fp)
        except Exception as e:
            logger.error(e)

    def load(self):
        if self.__dict__['loaded'] or self.__dict__['exists'] == False:
            return

        try:
            if self.__dict__['exists'] is None:
                self.__dict__['exists'] = os.path.exists(self.filename)

            with open(self.filename, 'rb') as fp:
                data = pickle.load(fp)
                for name, value in data.iteritems():
                    if name not in self.__dict__:
                        self.__setattr__(name, value)
                    else:
                        logger.debug("Don't overwrite existing data for: {0}".format(name))

            self.__dict__['loaded'] = True
        except Exception as e:
            logger.debug(e)
