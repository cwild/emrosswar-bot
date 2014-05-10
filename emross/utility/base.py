import logging

logger = logging.getLogger(__name__)


class BotLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        """
        Process the logging message and keyword arguments passed in to
        a logging call to insert contextual information. You can either
        manipulate the message itself, the keyword args or both. Return
        the message and kwargs modified (or not) to suit your needs.

        Normally, you'll only need to override this one method in a
        LoggerAdapter subclass for your specific needs.
        """
        try:
            kwargs['extra'].update(self.extra)
        except Exception:
            kwargs['extra'] = self.extra

        return msg, kwargs

class PushoverLogHandler(logging.StreamHandler):
    REQUIRES_EXPLICIT = True

    def emit(self, record):
        try:
            if getattr(record, 'pushover', self.REQUIRES_EXPLICIT == False):
                record.bot.pushover.send_message(self.format(record))
        except Exception as e:
            logger.exception(e)

class BotFormatter(logging.Formatter):
    def format(self, record):
        record.bot = getattr(record, 'bot', '')
        return logging.Formatter.format(self, record)

class EmrossMetaClass(type):
    def __new__(cls, name, bases, dct):
        dct['_logname'] = dct.get('__module__', name)
        return super(EmrossMetaClass, cls).__new__(cls, name, bases, dct)

class EmrossBaseObject(object):
    __metaclass__ = EmrossMetaClass

    def __init__(self, bot, *args, **kwargs):
        super(EmrossBaseObject, self).__init__(*args, **kwargs)
        self.bot = bot
        self.log = BotLoggerAdapter(logging.getLogger(self._logname), {'bot':bot})
