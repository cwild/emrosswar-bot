import logging

logger = logging.getLogger(__name__)


def safe_text(s):
    if isinstance(s, unicode):
        return s.encode('utf-8')
    elif isinstance(s, str):
        # Must be encoded in UTF-8
        return s.decode('utf-8')
    return s


class BotFormatter(logging.Formatter):
    def format(self, record):
        record.bot = record.__dict__.get('bot') or ''
        return logging.Formatter.format(self, record)

class BotInfo(object):
    def __init__(self, bot):
        self.bot = bot
        super(BotInfo, self).__init__()

    def __getitem__(self, name):
        try:
            return safe_text(self.bot._data.get('nick', ''))
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
        super(EmrossBaseObject, self).__init__(*args, **kwargs)
        self.bot = bot
        self.log = logging.LoggerAdapter(logging.getLogger(self._logname), BotInfo(bot))
