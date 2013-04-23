import logging

from emross.api import EmrossWar
EmrossWar.extend('ITEM', 'translation/%(lang)s/item_data.js')

logger = logging.getLogger(__name__)

class Item:
    ITEM_LIST = 'game/goods_api.php'
    ITEM_OP = 'game/goods_mod_api.php'

    def __init__(self, bot):
        self.bot = bot

    def find(self, items=[]):
        if items:
            ids = ','.join([str(item_id) for item_id in items])
            return self.bot.api.call(self.ITEM_LIST, extra=1, ids=ids)

    def list(self, page=1, type=3):
        """
        List goods from inventory

        'ret': {
            'max': 38,
            'item': [{
                'item': {
                    'up': 0,
                    'attr': [0, 0, 0, 15, 0, 0],
                    'num': 1,
                    'id': 12345678,
                    'sid': 69
                },
                'use': 0,
                'sale': 40000
            }]
        }
        """
        return self.bot.api.call(self.ITEM_LIST, action='goods_list', page=page, type=type)

    def use(self, city, id):
        return self.bot.api.call(self.ITEM_OP, action='use', city=city, id=id, num=1)

    def sell(self, city, id, **kwargs):
        return self.bot.api.call(self.ITEM_OP, action='sale', city=city, id=id, **kwargs)

    def upgrade(self, city, id):
        return self.bot.api.call(self.ITEM_OP, action='upgrade', city=city, id=id)


class ItemRank:
    COMMON = 0
    ELITE = 1
    RARE = 2
    BLESSED = 3


class ItemType:
    WEAPON = 1
    ARMOR = 2
    ITEM = 3
    RING = 4
    MOUNT = 5
    BOOK = 6


ITEMS = dict([(int(sid), item) for sid, item in EmrossWar.ITEM.iteritems()])

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    item = ITEMS[113]
    logger.info('Type: %s, Rank: %s' % (item['type'], item['rank']))

    logger.info(EmrossWar.ITEM[str(113)])
    logger.info(EmrossWar.ITEM[str(113)].get('name', 'UNKNOWN'))
