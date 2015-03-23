from __future__ import division

import math
import random

from emross.api import EmrossWar
from emross.exceptions import TradeException
from emross.item import inventory
from emross.resources import Resource
from emross.trade.trader import Trade
from emross.utility.task import Task
from emross.utility.remote_api import RemoteApi

from lib import six


from emross.utility import settings


class RemoteTrade(RemoteApi):
    DELETE = 'trade/delete'
    LIST = 'trade/list'
    SYNC = 'trade/sync'

    def delete(self, trade_ids, *args, **kwargs):
        ids = ','.join(trade_ids)
        return self.call(self.DELETE, method='DELETE', id=ids, *args, **kwargs)

    def list(self, *args, **kwargs):
        return self.call(self.LIST, *args, **kwargs)

    def sync(self, items, *args, **kwargs):
        items = self.json_encode(items)
        return self.call(self.SYNC, method='POST', trading=items, *args, **kwargs)

class AutoTrade(Task):
    INTERVAL = 5
    BUYER = 'buyer'
    SELLER = 'seller'

    def setup(self):
        self.remote = RemoteTrade(**settings.plugin_api)
        self.trade = Trade(self.bot)

    def process(self, mode=BUYER, *args, **kwargs):
        try:
            _process = getattr(self, 'process_{0}'.format(mode))
            return _process(*args, **kwargs)
        except (AttributeError, ValueError) as e:
            self.log.error(e)


    def process_buyer(self, interval=900, team=False, sleep=(4,5), delay=(0,15), *args, **kwargs):
        """Buy items specified by a remote api"""

        available = self.remote.list(method='GET',
                        server=self.bot.api.game_server,
                        team=int(team==True),
                        account=self.bot.userinfo.get('id')
                    )
        self.log.info('The trade listing has {0} available items.'.format(len(available['items'])))

        if len(available['items']) > 0:
            city = self.bot.richest_city()

            purchased, unavailable = [], []
            for item in available['items']:
                if city.resource_manager.meet_requirements({Resource.GOLD: int(item['price'])}, convert=False):
                    json = self.trade.buy_item(city, item['id'], sleep=sleep)

                    if json['code'] == EmrossWar.SUCCESS:
                        city.resource_manager.modify_amount_of(Resource.GOLD, -int(item['price']))
                        purchased.append(item['id'])
                    elif json['code'] == EmrossWar.INSUFFICIENT_GOLD:
                        self.log.info(six.u('Not enough gold at {0} to purchase item {1}').format(city, item['id']))
                        break
                    elif json['code'] == EmrossWar.ITEM_DOES_NOT_EXIST:
                        unavailable.append(item['id'])

            if purchased:
                self.log.debug('We managed to buy the following ids from trade: {0}'.format(purchased))

            if unavailable:
                self.log.debug('The following trade ids were not available for purchase: {0}'.format(unavailable))

            to_delete = purchased + unavailable
            if to_delete:
                self.remote.delete(to_delete)

        try:
            _delay = random.randint(*delay)
        except TypeError:
            _delay = random.randint(0, 15)

        self.sleep(interval + _delay)


    def process_seller(self,
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
        except (IndexError, TypeError) as e:
            city = self.bot.poorest_city()

        self.log.debug('Sell trade items from city "{0}"'.format(city.name))

        waiting = self.trade.list_all(city, funcs=[self.trade.list_waiting])
        trading = self.trade.list_all(city, funcs=[self.trade.list_trading])

        remaining = min(Trade.MAX_ITEMS, limit) - len(waiting) - len(trading)
        can_sell = True

        gold = city.resource_manager.get_amount_of(Resource.GOLD)
        if min_gold:
            can_sell = gold < min_gold
            self.log.debug('Sell items only if current gold at this city is less than the min gold')

        if max_gold:
            can_sell = gold < max_gold
            self.log.debug('Sell items only if current gold at this city is less than the max gold')

        if can_sell is False:
            self.log.info('Not selling. Current gold={0}, Min gold={1}, Max gold={2}'.format(gold, min_gold, max_gold))
        elif remaining > 0:
            self.log.debug('We have {0} spare slots to trade items!'.format(remaining))

            for_sale = []
            for search_item in items:
                sellable = self.bot.find_inventory_item(search_item)
                if sellable:
                    for_sale.extend(sellable)

            try:
                sellable_items = sum([int(num) for id, num, sale_gold in for_sale])
                # Flatten the for-sale list
                for_sale[:] = [id for id, num, sale_gold in for_sale for n in xrange(num)]
            except ValueError:
                sellable_items = 0

            self.log.debug('There are {0} sellable items'.format(sellable_items))

            shortfall = remaining - sellable_items
            item_price = None
            if shortfall > 0:
                self.log.info('Buy {0} items to sell'.format(shortfall))
                item_id, item_price, item_attr = self.bot.shop.find_item(city, search_item)
                gold = city.resource_manager.get_amount_of(Resource.GOLD)

                for _ in xrange(shortfall):
                    if gold < item_price:
                        self.log.info(six.u('Not enough gold at {0} to buy {1} from shop at cost {2}').format(city, item_id, item_price))
                        break

                    try:
                        inventory_id = self.bot.shop.buy(city, search_item)
                        for_sale.append(inventory_id)
                    except (KeyError, TypeError):
                        self.log.debug('Encountered an error while purchasing from shop')

            self.log.debug('For Sale: {0}'.format(for_sale))

            total = price
            if vary > 0:
                total += random.randint(1,vary)
            cost = int(math.ceil(total / Trade.SELLING_FEE))

            while remaining > 0:
                gold = city.resource_manager.get_amount_of(Resource.GOLD)

                if gold == 0:
                    self.log.info('No gold available to post an item')
                    break
                elif gold < cost:
                    if min_gold:
                        self.bot.clearout_inventory(city, use_items=True, sell_items=True)
                        city.expire()
                        gold = city.resource_manager.get_amount_of(Resource.GOLD)
                        total = min(total, gold*Trade.SELLING_FEE)

                        if not item_price:
                            item_id, item_price, item_attr = self.bot.shop.find_item(city, search_item)

                        # Only actually sell if we will make at least 10%
                        if total < (item_price * (1+(100/Trade.SELLING_FEE))):
                            self.log.debug('No point selling as we would not make a profit!')
                            break
                    else:
                        self.log.info('Not enough gold to cover the cost of posting an item')
                        self.sleep(600)
                        break

                try:
                    inv_id = for_sale.pop()
                    self.log.info('Selling item {0} for {1} gold on trade'.format(inv_id, total))
                    self.trade.sell_item(city, inv_id, total)
                    self.sleep(900)
                except IndexError:
                    self.log.debug('No more sellable items left to post')
                    break
                except TradeException as e:
                    self.log.info(e)
                    self.sleep(900)
                    break

                remaining -= 1

        else:
            self.log.info('We have no space to post any more items on trade')
            self.sleep(900)


        self.log.debug('Sync trade list to remote api, trading items {0}'.format(trading))
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
