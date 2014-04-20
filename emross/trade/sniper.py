from emross.api import EmrossWar
from emross.item import item
from emross.resources import Resource
from emross.trade.trader import Trade
import time

RARES = set([k for k, v in item.ITEMS.iteritems() if v['rank'] >= item.ItemRank.RARE])

class TradeSniper:
    def __init__(self, bot):
        self.bot = bot
        self.trader = Trade(bot)

    def snipe(self, duration=10, delay=0.5, items=RARES):

        endtime = time.time() + duration

        while time.time() < endtime:
            print 'searching...'
            city = self.bot.richest_city()
            listing = self.trader.list_market(city)

            for _item in listing['ret']['item']:
                trade_id, item_id, price = _item[:3]

                if item_id in items:
                    city = self.bot.richest_city()
                    gold = city.resource_manager.get_amount_of(Resource.GOLD)

                    if gold >= price:
                        json = self.trader.buy_item(city, trade_id)
                        if json['code'] == EmrossWar.SUCCESS:
                            print 'Bought item %d for %d gold' % (item_id, price)
                            try:
                                city.resource_manager.modify_amount_of(Resource.GOLD, -int(price))
                            except Exception, e:
                                print e

            time.sleep(delay)


if __name__ == '__main__':
    from bot import bot
    bot.update()

    sniper = TradeSniper(bot)
    sniper.snipe(duration=1)