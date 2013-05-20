import logging

logger = logging.getLogger(__name__)

class BotFormatter(logging.Formatter):
    def format(self, record):
        record.__dict__['bot'] = record.__dict__.get('bot') or ''
        return logging.Formatter.format(self, record)

class BotInfo(object):
    def __init__(self, bot):
        self.bot = bot
        super(BotInfo, self).__init__()

    def __getitem__(self, name):
        try:
            return str(self.bot.userinfo['nick'].encode('utf-8'))
        except Exception as e:
            logger.exception(e)
            return ''

    def __iter__(self):
        return iter(['bot'])

class EmrossMetaClass(type):
    def __new__(cls, name, bases, dct):
        dct['_logname'] = dct.get('__module__', name)
        return super(EmrossMetaClass, cls).__new__(cls, name, bases, dct)

class EmrossBaseObject(object):
    __metaclass__ = EmrossMetaClass

    def __init__(self, bot, *args, **kwargs):
        super(EmrossBaseObject, self).__init__()
        self.bot = bot
        self.log = logging.LoggerAdapter(logging.getLogger(self._logname), BotInfo(bot))
