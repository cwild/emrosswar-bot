from emross.utility.base import EmrossBaseObject

class EmrossHandler(EmrossBaseObject):
    def __init__(self, bot, *args, **kwargs):
        super(EmrossHandler, self).__init__(bot)
        self.args = args
        self.kwargs = kwargs

    def process(self, json):
        pass