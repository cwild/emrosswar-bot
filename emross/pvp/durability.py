import logging
logger = logging.getLogger(__name__)
import time

from emross.api import EmrossWar
from emross.resources import Resource
from emross.utility.task import Task


class AutoDurability(Task):
    INTERVAL = 5
    DURABILITY_COST = 100000

    def process(self, start_below=100, stop_below=0, *args, **kwargs):
        if not self.bot.pvp:
            self.sleep(86400)
            return True

        for city in self.bot.cities:
            protection_end = self.bot.userinfo.get('p_end', 0)
            if protection_end > time.time():
                wait = protection_end - time.time()
                self.sleep(wait)
                logger.info('We are still under protection, try again in %d seconds' % wait)
                return True


            json = self.bot.api.call(self.bot.USERINFO_URL, action='g_cd')

            if json['code'] == EmrossWar.SUCCESS:
                gold_cooldown, _, _, _, durability, \
                    durability_cooldown, sleep_time = json['ret']

                logger.info('Castle durability=%d (cooldown %d secs), remaining sleep time=%d secs' % \
                    (durability, durability_cooldown, sleep_time))

                if durability_cooldown > 0:
                    self.sleep(durability_cooldown)
                    logger.info('Wait %d seconds before increasing durability' % durability_cooldown)
                elif durability < stop_below:
                    logger.info('Durability is %d and only increase when above %d' %
                        (durability, stop_below))
                    self.sleep(86400)
                    return True
                elif durability < start_below:

                    if city.resource_manager.get_amount_of(Resource.GOLD) < self.DURABILITY_COST:
                        gold_required = self.DURABILITY_COST - city.resource_manager.get_amount_of(Resource.GOLD)
                        logger.info('We need 100k gold to increase durability, we need a further %d gold' \
                            % gold_required)

                        if not self.bot.find_gold_for_city(city, gold_required, unbrick=True):
                            logger.info('Unable to find enough gold, try again in 5 minutes')
                            self.sleep(300)
                            return True

                    json = self.bot.api.call(city.GET_CITY_INFO, city=city.id, action='op_pop')

                    if json['code'] == EmrossWar.SUCCESS:
                        durability, countdown, gold = json['ret']
                        logger.info('Castle durability is now %d, try again in %d secs' % \
                            (durability, countdown))
                        city.resource_manager.set_amount_of(Resource.GOLD, gold)
                        self.sleep(countdown)
