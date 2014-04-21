import re

from emross.api import EmrossWar
from emross.api.cache import EmrossDataHandler


class ItemDataHandler(EmrossDataHandler):
    iteritems = lambda self: self.data.iteritems()

    def name(self, name=None):
        for item, data in self.iteritems():
            if data['name'] == name:
                return item, data

    def search(self, name=None):
        for item, data in self.iteritems():
            if re.match(name, data['name'], re.IGNORECASE):
                return item, data

EmrossWar.extend('ITEM', 'translation/%(lang)s/item_data.js', model=ItemDataHandler)
