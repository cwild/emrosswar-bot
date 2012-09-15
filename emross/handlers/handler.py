class EmrossHandler(object):
    def __init__(self, bot, *args, **kwargs):
        super(EmrossHandler, self).__init__(*args, **kwargs)
        self.bot = bot

    def process(self, json):
        pass