from __future__ import division

from emross.api import EmrossWar
from emross.exceptions import TradeException
from emross.item import inventory
from emross.resources import Resource
from emross.utility.task import Task
from emross.utility.remote_api import RemoteApi
from trader import Trade

import math
import random

import settings

import logging
logger = logging.getLogger(__name__)


class RemoteTrade(RemoteApi):
    DELETE = 'trade/delete'
    LIST = 'trade/list'
    SYNC = 'trade/sync'

    def delete(self, trade_ids, *args, **kwargs):
        ids = ','.join(trade_ids)
        json = self.call(self.DELETE, method='DELETE', id=ids, *args, **kwargs)
        return json

    def list(self, *args, **kwargs):
        json = self.call(self.LIST, *args, **kwargs)
        return json

    def sync(self, items, *args, **kwargs):
        items = self.json_encode(items)
        json = self.call(self.SYNC, method='POST', trading=items, *args, **kwargs)
        return json

class AutoTrade(Task):
    INTERVAL = 5
    BUYER = 'buyer'
    SELLER = 'seller'

    def setup(self):
        self.remote = RemoteTrade(**settings.plugin_api)
        self.trade = Trade(self.bot)

    def process(self, mode=BUYER, *args, **kwargs):
        if mode == AutoTrade.SELLER:
            _process = self.seller_process
        elif mode == AutoTrade.BUYER:
            _process = self.buyer_process
        else:
            return None

        try:
            return _process(*args, **kwargs)
        except ValueError as e:
            logger.debug(e)
            return None


    def buyer_process(self, interval=900, team=False, sleep=(4,5)):
        """Buy items specified by a remote api"""

        available = self.remote.list(method='GET', server=self.bot.api.game_server, team=int(team==True))
        logger.info('The trade listing has %d available items.' % len(available['items']))
        logger.debug('Available items: %s' % available['items'])

        if len(available['items']) > 0:
            city = self.bot.richest_city()

            purchased, unavailable = [], []
            for item in available['items']:
                gold = city.resource_manager.get_amount_of(Resource.GOLD)
                if gold > int(item['price']):
                    json = self.trade.buy_item(city, item['id'], sleep=sleep)

                    if json['code'] == EmrossWar.SUCCESS:
                        city.resource_manager.set_amount_of(Resource.GOLD, gold-int(item['price']))
                        purchased.append(item['id'])
                    elif json['code'] == EmrossWar.INSUFFICIENT_GOLD:
                        logger.info('Not enough gold at city "%s" to purchase item %d' % (city.name, item['id']))
                        break
                    elif json['code'] == EmrossWar.ITEM_DOES_NOT_EXIST:
                        unavailable.append(item['id'])

            if purchased:
                logger.debug('We managed to buy the following ids from trade: %s' % purchased)

            if unavailable:
                logger.debug('The following trade ids were not available for purchase: %s' % unavailable)

            to_delete = purchased + unavailable
            if to_delete:
                self.remote.delete(to_delete)

        self.sleep(interval)


    def seller_process(self,
        items=[inventory.ALLIANCE_TOKEN],
        price=1000000,
        vary=1000,
        limit=Trade.MAX_ITEMS,
        city_index=None,
        min_gold=None,
        max_gold=None,
        *args, **kwargs):
        """Buy items to sell on the market."""

        try:
            city = self.bot.cities[city_index]
        except (IndexError, TypeError), e:
            city = self.bot.poorest_city()

        logger.debug('Sell trade items from city "%s"' % city.name)

        waiting = self.trade.list_all(city, funcs=[self.trade.list_waiting])
        trading = self.trade.list_all(city, funcs=[self.trade.list_trading])

        remaining = min(Trade.MAX_ITEMS, limit) - len(waiting) - len(trading)
        can_sell = True

        gold = city.resource_manager.get_amount_of(Resource.GOLD)
        if min_gold:
            can_sell = gold > min_gold
            logger.debug('Sell items only if current gold at this city is less than the min gold')

        if max_gold:
            can_sell = gold < max_gold
            logger.debug('Sell items only if current gold at this city is less than the max gold')

        if can_sell is False:
            logger.info('Not selling. Current gold=%d, Min gold=%s, Max gold=%s' % (gold, str(min_gold), str(max_gold)))
        elif remaining > 0:
            logger.debug('We have %d spare slots to trade items!' % remaining)

            for_sale = []
            for search_item in items:
                sellable = self.bot.find_inventory_item(search_item)
                if sellable:
                    for_sale.extend(sellable)

            try:
                sellable_items = sum([int(num) for id, num in for_sale])
                # Flatten the for-sale list
                for_sale[:] = [id for id, num in for_sale for n in xrange(num)]
            except ValueError:
                sellable_items = 0

            logger.debug('There are %d sellable items' % sellable_items)

            shortfall = remaining - sellable_items
            if shortfall > 0:
                logger.info('Buy %d items to sell' % shortfall)
                item_id, item_price, item_attr = self.bot.shop.find_item(city, search_item)
                gold = city.resource_manager.get_amount_of(Resource.GOLD)

                for _ in xrange(shortfall):
                    if gold < item_price:
                        logger.info('Not enough gold at city "%s" to buy %d from shop at cost %d' % (city.name, item_id, item_price))
                        break

                    try:
                        inventory_id = self.bot.shop.buy(city, search_item)
                        for_sale.append(inventory_id)
                    except (KeyError, TypeError):
                        logger.debug('Encountered an error while purchasing from shop')

            logger.debug('For Sale: %s' % for_sale)

            total = price
            if vary > 0:
                total += random.randint(1,vary)
            cost = int(math.ceil(total / Trade.SELLING_FEE))

            while remaining > 0:
                gold = city.resource_manager.get_amount_of(Resource.GOLD)

                if gold < cost:
                    logger.info('Not enough gold to cover the cost of posting an item')
                    self.sleep(600)
                    break

                try:
                    inv_id = for_sale.pop()
                    logger.info('Selling item %d for %d gold on trade' % (inv_id, total))
                    self.trade.sell_item(city, inv_id, total)
                    self.sleep(900)
                except IndexError:
                    logger.debug('No more sellable items left to post')
                    break
                except TradeException, e:
                    logger.info(e)
                    self.sleep(900)
                    break

                remaining -= 1

        else:
            logger.info('We have no space to post any more items on trade')
            self.sleep(900)


        logger.debug('Sync trade list to remote api, trading items %s' % trading)
        self.remote.sync(server=self.bot.api.game_server, user_id=self.bot.userinfo['id'], items=trading)
        self.sleep(300)


if __name__ == '__main__':
    from bot import bot
    from emross.item import inventory

    bot.update()
    trade_bot = AutoTrade(bot)

    #trade_bot.process(AutoTrade.BUYER, *(15,), **{'team': True})

    trade_bot.process(AutoTrade.SELLER, [inventory.ALLIANCE_TOKEN],
            **{'price':10000, 'vary':500, 'limit':2, 'city_index':-1})
