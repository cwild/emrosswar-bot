from emross.item import item
from emross.resources import Resource

import logging
logger = logging.getLogger(__name__)

class Shop:
    SHOP_URL = 'game/sys_shop_api.php'

    GOLD_ITEMS = 'list_goldshopitems'

    def __init__(self, bot):
        self.bot = bot

    def list(self, city, action=GOLD_ITEMS, type=item.ItemType.WEAPON):
        """
        {"code":0,"ret":{"item":[113,190],"price":[10000,100000],"attr":[[0,0,0,0,0,0],[0,0,0,0,0,0]]}}
        """
        type = self._item_type(type)
        logger.info('Listing shop items, %s of type %d' % (action, type))
        res = self.bot.api.call(self.SHOP_URL, action=action, type=type, city=city.id)
        return res


    def buy(self, city, search_item):
        """
        action=purchase&type=3&city=12345&id=113
        {"code":0,"ret":{"gold":6725626,"itemid":"9876543"}}
        """
        item_id, item_type, item_rank = search_item
        item_type = self._item_type(item_type)

        res = self.bot.api.call(self.SHOP_URL, action='purchase', id=item_id, type=item_type, city=city.id)
        city.resource_manager.set_amount_of(Resource.GOLD, res['ret']['gold'])

        return int(res['ret']['itemid'])

    def find_item(self, city, search_item):
        item_id, item_type, item_rank = search_item
        logger.info('Find item %d in shop' % item_id)

        shop_items = self.list(city, type=item_type)

        try:
            items = shop_items['ret']
            pos = items['item'].index(item_id)
            shop_price = items['price'][pos]
            attributes = items['attr'][pos]
        except ValueError:
            logger.info('Cannot find item %d in the shop.' % item_id)

        return (item_id, shop_price, attributes)

    def _item_type(self, item_type):
        it = item.ItemType
        if item_type not in [it.WEAPON, it.ARMOR, it.RING, it.MOUNT, it.BOOK]:
            item_type = it.ITEM
        return item_type
