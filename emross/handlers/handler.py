class EmrossHandler(object):
    def __init__(self, bot, *args, **kwargs):
        super(EmrossHandler, self).__init__()
        self.bot = bot
        self.args = args
        self.kwargs = kwargs

    def process(self, json):
        pass