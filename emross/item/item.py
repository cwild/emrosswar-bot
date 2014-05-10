from emross.api import EmrossWar
from emross.utility.base import EmrossBaseObject


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

class Item(EmrossBaseObject):
    ITEM_LIST = 'game/goods_api.php'
    ITEM_OP = 'game/goods_mod_api.php'

    def find(self, items=[]):
        if items:
            ids = ','.join([str(item_id) for item_id in items])
            return self.bot.api.call(self.ITEM_LIST, extra=1, ids=ids)

    def list(self, page=1, type=ItemType.ITEM):
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

    def list_enhance(self, type=ItemType.WEAPON):
        return self.bot.api.call(self.ITEM_LIST, action='listupdate', type=type)

    def use(self, city, id, num=1):
        """
        {'code': 0, 'ret': {
            'gold': 3000, 'food': 0,
            'vipbuff': 0, 'gen': 0,
            'item': [],
            'wood': 0, 'rumor': 0,
            'iron': 0, 'ep': 0, 'gem': 0, 'buff': ''}}
        """
        return self.bot.api.call(self.ITEM_OP, action='use', city=city, id=id, num=num)

    def sell(self, city, id, **kwargs):
        return self.bot.api.call(self.ITEM_OP, action='sale', city=city, id=id, **kwargs)

    def upgrade(self, city, id):
        return self.bot.api.call(self.ITEM_LIST, action='upgrade', city=city.id, id=id)

    def downgrade(self, city, id):
        return self.bot.api.call(self.ITEM_LIST, action='degrade', city=city.id, id=id)


ITEMS = dict([(int(sid), item) for sid, item in EmrossWar.ITEM.iteritems()])

if __name__ == "__main__":
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.DEBUG)

    item = ITEMS[113]
    logger.info('Type: {0}, Rank: {1}'.format(item['type'], item['rank']))

    logger.info(EmrossWar.ITEM[str(113)])
    logger.info(EmrossWar.ITEM[str(113)].get('name', 'UNKNOWN'))
