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

class EmrossBaseObject(object):
    def __init__(self, bot, name=__name__, *args, **kwargs):
        super(EmrossBaseObject, self).__init__()
        self.bot = bot
        self.log = logging.LoggerAdapter(logging.getLogger(name), BotInfo(bot))
