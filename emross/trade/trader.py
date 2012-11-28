from emross.api import EmrossWar
from emross.exceptions import TradeException

import logging
logger = logging.getLogger(__name__)

class Trade:
    TRADE_URL = 'game/safe_goods_api.php'
    MARKET_URL = 'game/safe_market_api.php'


    LIST_ITEM = 'list_auction_item'
    INVENTORY_ITEMS = 'list_invitem'
    SELL_ITEM = 'my_goods_safe'

    def __init__(self, bot):
        self.bot = bot

    def _list(self, type, city, page=1):
        return self.bot.api.call(self.TRADE_URL, action=self.LIST_ITEM, type=type, city=city, page=page)

    def list_waiting(self, city, *args, **kwargs):
        json = self._list('will', city=city, *args, **kwargs)
        return json

    def list_trading(self, city, *args, **kwargs):
        json = self._list('', city=city, *args, **kwargs)
        return json

    def sell_item(self, city, id, price):
        json = self.bot.api.call(self.TRADE_URL, action=self.SELL_ITEM, city=city, id=id, safe_num=1, price=price)

        if json['code'] != EmrossWar.SUCCESS:
            logger.info('Problem selling item %d at city %s for %d gold' % (item, city.name, price))
            raise TradeException

        return EmrossWar.SUCCESS

    def buy_item(self, city, id):
        """
        Purchase an item from trade.
        """
        json = self.bot.api.call(self.MARKET_URL, action='purchasing', city=city, id=id)
        return json['code'] == EmrossWar.SUCCESS
