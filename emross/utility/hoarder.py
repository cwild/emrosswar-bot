from lib import six

from emross.api import EmrossWar
from emross.item import inventory
from emross.resources import Resource
from emross.utility.task import Task

GOLD_CONVERSION_URL = 'game/gold_local_market_api.php'

class GoldHoarder(Task):
    INTERVAL = 900
    CONVERSION_PENALTY = 1.1

    CONVERSION_OPTIONS = [
        (inventory.GOLD_BULLION[0], 1, 1000),
        (inventory.GOLD_BRICK[0], 2, 10000)
    ]

    NOT_ALLOWED_DURING_WAR = 809

    def process(self, retry_after_fail=300, *args, **kwargs):
        json = self.bot.api.call(self.bot.USERINFO_URL, action='g_cd')
        conversion_cooldown = json['ret'][0]

        delay = None

        if conversion_cooldown > 0:
            self.log.info('Cooldown of {0} seconds before conversion is possible'.format(conversion_cooldown))
            delay = min(conversion_cooldown, self.INTERVAL)
        else:
            city = self.bot.richest_city()

            for gold_id, gold_type, gold_amount in self.CONVERSION_OPTIONS[::-1]:
                cost = gold_amount * self.CONVERSION_PENALTY
                qty = 0
                while city.resource_manager.meet_requirements({Resource.GOLD: cost*(qty+1)}, convert=False):
                    qty += 1

                if qty:
                    self.log.info(six.u('Try to convert {0} into {1}*"{2}" at {city}').format(\
                        EmrossWar.LANG.get('COIN', 'gold'),
                        qty,
                        EmrossWar.ITEM[str(gold_id)].get('name'),
                        city=city)
                    )

                    json = self.bot.api.call(GOLD_CONVERSION_URL, city=city.id, type=gold_type, num=qty)
                    if json['code'] == EmrossWar.SUCCESS:
                        city.resource_manager.modify_amount_of(Resource.GOLD, -int(json['ret']))
                        delay = min(int(json['ext'][0]), self.INTERVAL)
                        break
                    elif json['code'] == self.NOT_ALLOWED_DURING_WAR:
                        self.log.info('Cannot convert during war, try again in {0} seconds'.format(\
                            retry_after_fail))
                        self.sleep(retry_after_fail)
                        break

        self.sleep(delay or self.INTERVAL)
