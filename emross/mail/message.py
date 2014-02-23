from emross.mail import WAR_RESULT_INFO, WAR_RESULT_LIST
from emross.utility.base import EmrossBaseObject


class Mail(EmrossBaseObject):

    def __init__(self, bot, id, data):
        super(Mail, self).__init__(bot)
        self.id = id
        self.data = data
        self.message = None
        self.processed = False

    def fetch(self):
        self.message = self.bot.api.call(WAR_RESULT_INFO, id=self.id)['ret']

    def delete(self):
        return self.bot.api.call(WAR_RESULT_LIST, action='delete', id=self.id)

    def add_fav(self, cat):
        return self.bot.favourites.add(wid=self.id, cat=cat)
