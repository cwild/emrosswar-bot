import emross
from emross.api import EmrossWar, cache_ready
from emross.resources import Resource
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

    @emross.defer.inlineCallbacks
    def find(self, items=[]):
        if items:
            ids = ','.join([str(item_id) for item_id in items])
            json = yield self.bot.api.call(self.ITEM_LIST, extra=1, ids=ids)
            emross.defer.returnValue(json)

        emross.defer.returnValue([])

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

    @emross.defer.inlineCallbacks
    def use(self, city, id, num=1):
        """
        {'code': 0, 'ret': {
            'gold': 3000, 'food': 0,
            'vipbuff': 0, 'gen': 0,
            'item': [],
            'wood': 0, 'rumor': 0,
            'iron': 0, 'ep': 0, 'gem': 0, 'buff': ''}}
        """
        json = yield self.bot.api.call(self.ITEM_OP, action='use', city=city.id, id=id, num=num)
        if json['code'] == EmrossWar.SUCCESS:
            self.bot.inventory.adjust_item_stock(id, -num)

        emross.defer.returnValue(json)

    @emross.defer.inlineCallbacks
    def sell(self, city, id, **kwargs):
        json = yield self.bot.api.call(self.ITEM_OP, action='sale', city=city.id, id=id, **kwargs)

        if json['code'] == EmrossWar.SUCCESS:
            self.bot.inventory.adjust_item_stock(id, -kwargs.get('num', 0))

        emross.defer.returnValue(json)

    def upgrade(self, city, id):
        return self.bot.api.call(self.ITEM_LIST, action='upgrade', city=city.id, id=id)

    @emross.defer.inlineCallbacks
    def downgrade(self, city, id):
        json = yield self.bot.api.call(self.ITEM_LIST, action='degrade', city=city.id, id=id)
        if json['code'] == EmrossWar.SUCCESS:
            city.resource_manager.set_amount_of(Resource.GOLD, json['ret'][1])
        emross.defer.returnValue(json)


ITEMS = cache_ready(lambda: globals().update(
    {'ITEMS': dict([(int(sid), item) for sid, item in EmrossWar.ITEM.iteritems()])}
))


if __name__ == "__main__":
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.DEBUG)

    def test():
        item = ITEMS[113]
        logger.info('Type: {0}, Rank: {1}'.format(item['type'], item['rank']))

        logger.info(EmrossWar.ITEM[str(113)])
        logger.info(EmrossWar.ITEM[str(113)].get('name', 'UNKNOWN'))

    from emross import reactor
    cache_ready(test)
    cache_ready(lambda: reactor.stop())
    reactor.run()
