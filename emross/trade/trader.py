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

    SELLING_FEE = 10
    MAX_ITEMS = 20

    TRADE_LIMIT_REACHED = 3605

    def __init__(self, bot):
        self.bot = bot

    def _list(self, type, city, url=TRADE_URL, page=1, *args, **kwargs):
        return self.bot.api.call(url, type=type, city=city.id, page=page, *args, **kwargs)

    def list_waiting(self, city, *args, **kwargs):
        json = self._list('will', action=self.LIST_ITEM, city=city, *args, **kwargs)
        return json

    def list_trading(self, city, *args, **kwargs):
        json = self._list(None, action=self.LIST_ITEM, city=city, *args, **kwargs)
        return json

    def list_market(self, city, *args, **kwargs):
        json = self._list(type=1, city=city, url=self.MARKET_URL)
        return json

    def list_all(self, city, funcs=[]):
        result = []
        for func in funcs:
            page = 1

            while True:
                json = func(city, page=page)
                result.extend(json['ret']['item'])

                page += 1
                if page > json['ret']['max']:
                    break
        return result

    def sell_item(self, city, id, price):
        json = self.bot.api.call(self.TRADE_URL, action=self.SELL_ITEM, city=city.id, id=id, safe_num=1, price=price)

        if json['code'] == self.TRADE_LIMIT_REACHED:
            raise TradeException, 'Maximum number of trade items has been reached'

        if json['code'] != EmrossWar.SUCCESS:
            logger.warning('Problem selling item %d at city %s for %d gold' % (id, city.name, price))
            raise TradeException

        return EmrossWar.SUCCESS

    def buy_item(self, city, id, *args, **kwargs):
        """
        Purchase an item from trade.
        """
        logger.info('Attempting to buy item %s from city "%s"' % (str(id), city.name))
        json = self.bot.api.call(self.MARKET_URL, action='purchasing', city=city.id, id=id, *args, **kwargs)
        return json
