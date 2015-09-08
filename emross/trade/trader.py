from __future__ import division

from emross.api import EmrossWar
from emross.exceptions import TradeException
from emross.resources import Resource
from emross.utility.controllable import Controllable

from lib import six

class Trade(Controllable):
    COMMAND = 'trade'

    TRADE_URL = 'game/safe_goods_api.php'
    MARKET_URL = 'game/safe_market_api.php'

    LIST_ITEM = 'list_auction_item'
    INVENTORY_ITEMS = 'list_invitem'
    SELL_ITEM = 'my_goods_safe'

    SELLING_FEE = 10
    MAX_ITEMS = 20

    TRADE_LIMIT_REACHED = 3605

    P2P_BUYER_COST = 10
    P2P_SELLER_DEFAULT_PRICE = 1

    def _list(self, type, city, url=TRADE_URL, page=1, *args, **kwargs):
        return self.bot.api.call(url, type=type, city=city.id, page=page, *args, **kwargs)

    def list_waiting(self, city, *args, **kwargs):
        return self._list('will', action=self.LIST_ITEM, city=city, *args, **kwargs)

    def list_trading(self, city, *args, **kwargs):
        return self._list(None, action=self.LIST_ITEM, city=city, *args, **kwargs)

    def list_market(self, city, *args, **kwargs):
        return self._list(type=1, city=city, url=self.MARKET_URL)

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

    def sell_item(self, city, id, price, player=None, **kwargs):
        """
        Given a city, sell the specified item id for the specified price.
        If player is supplied then do a p2p trade
        """
        json = self.bot.api.call(self.TRADE_URL, action=self.SELL_ITEM,
                    city=city.id, id=id, safe_num=1, price=price,
                    player_pname=player)

        if json['code'] == self.TRADE_LIMIT_REACHED:
            raise TradeException('Maximum number of trade items has been reached')

        if json['code'] != EmrossWar.SUCCESS:
            self.log.warning(six.u('Problem selling item {0} at {1} for {2} gold').format(id, city, price))
            raise TradeException(json.get('ret') or 'Problem selling item')

        if player:
            msg = gettext('P2P trade item {id} to "{player}" for {price} {resource}').format(\
                id=id, player=player, price=price, resource=EmrossWar.LANG.get('COIN', 'gold')
            )
            self.chat.send_message(msg, event=kwargs.get('event'))

        return EmrossWar.SUCCESS

    def buy_item(self, city, id, *args, **kwargs):
        """
        Purchase an item from trade.
        """
        self.log.info(six.u('Attempting to buy item {0} from {1}').format(id, city.name))
        return self.bot.api.call(self.MARKET_URL, action='purchasing', city=city.id, id=id, *args, **kwargs)

    @Controllable.restricted
    def action_p2p(self, event, search_item=None, *args, **kwargs):
        """
        Player-to-Player trade. Sell the listed `item`
        """
        player = kwargs.get('player') or event.player_name
        price = int(kwargs.get('price', self.P2P_SELLER_DEFAULT_PRICE))

        try:
            items = [int(kwargs['sid'])]
        except (KeyError, ValueError):
            items = self.bot.inventory.find_search_items_from_names(search_item)

        self.log.debug(items)

        if len(items) > 1:
            self.chat.send_message(\
                gettext('You need to be more specific as the following items match:'),
                event=event
            )

            for item in items:
                try:
                    name = EmrossWar.ITEM[str(item)]['name']
                except KeyError:
                    name = gettext('Unknown item')

                self.chat.send_message(gettext('sid={0}, name={1}').format(\
                    item, name),
                    event=event
                )

            self.chat.send_message(\
                gettext('You could try using the item number instead eg. sid=1234'),
                event=event
            )
            return

        sellable_item = None

        for item in items:
            for item_id, data in self.bot.inventory.data[item].iteritems():
                try:
                    if int(data['lockinfo']['locked']) == 1:
                        self.chat.send_message(gettext('That item is locked for {0}!').format(\
                            self.bot.human_friendly_time(data['lockinfo']['secs'])), event=event)
                        continue
                except KeyError:
                    pass

                if int(data['sale']) > 0:
                    sellable_item = item_id
                    break

        if not sellable_item:
            self.chat.send_message(gettext("I couldn't find that item, no deal!"), event=event)
            return

        city = self.bot.richest_city()
        cost = price * (self.SELLING_FEE / 100)

        if city.resource_manager.meet_requirements({Resource.GOLD: cost}, **kwargs):
            result = self.sell_item(city, sellable_item, price, player.encode('utf8'), event=event)

            if result == EmrossWar.SUCCESS:
                self.chat.send_message(gettext("Don't forget to buy that item, you hear?"), event=event)
            else:
                self.chat.send_message(gettext("Something didn't go to plan.."), event=event)
        else:
            self.chat.send_message(gettext('That would cost me too much!'), event=event)


if __name__ == "__main__":
    id, player, price = 1, six.u('test \xf3 player'), 123

    msg = gettext('P2P trade item {id} to "{player}" for {price} {resource}').format(\
        id=id, player=player, price=price, resource=EmrossWar.LANG.get('COIN', 'gold')
    )
    print msg
