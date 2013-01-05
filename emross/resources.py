import math

import logging
logger = logging.getLogger(__name__)

from emross.api import EmrossWar
from emross.exceptions import EmrossWarException

class Resource:
    FOOD = 'f'
    GOLD = 'g'
    IRON = 'i'
    WOOD = 'w'

    OFFSETS = {
        FOOD: 4,
        GOLD: 2,
        IRON: 8,
        WOOD: 6
    }

class ResourceManager:
    LOCAL_MARKET_URL = 'game/local_market_api.php'

    def __init__(self, bot, city):
        self.bot = bot
        self.city = city
        self._data = None

    @property
    def data(self):
        if self._data is None:
            """{"code":0,"ret":{"g2w":0.06,"g2f":0.13,"g2i":0.1,"w2g":17,"f2g":80,"i2g":11}}"""
            json = self.bot.api.call(self.LOCAL_MARKET_URL, city = self.city.id)
            self._data = json['ret']

        return self._data

    def conversion_rate(self, from_res, to_res):
        return self.data.get('%s2%s' % (from_res, to_res), None)

    def convert(self, from_res, to_res, amount=0):
        cvr = '%s2%s' % (from_res, to_res)
        conversion = {cvr: amount}
        logger.debug('Convert %s %d' % (cvr, amount))

        if amount:
            self._convert(**conversion)


    def _convert(self, **kwargs):
        logger.debug('Exchanging resources %s' % (kwargs))
        json = self.bot.api.call(self.LOCAL_MARKET_URL, city = self.city.id, reso_put='giveput', **kwargs)

        if json['code'] == EmrossWar.SUCCESS:
            for res, amt in json['ret'].iteritems():
                logger.debug('Setting %s resource to %d' % (res,amt))
                self.set_amount_of(res, amt)

        return json

    def get_amounts_of(self, resource):
        offset = Resource.OFFSETS[resource]
        return self.city.data[offset:offset+2]

    def get_amount_of(self, resource, idx=0):
        return self.get_amounts_of(resource)[idx]

    def set_amount_of(self, resource, amount):
        self.city.data[Resource.OFFSETS[resource]] = amount

    def meet_requirements(self, resource_levels, convert=True):
        conversion = {}
        total_gold = 0
        for res, amt in resource_levels.iteritems():
            if res != Resource.GOLD:
                shortfall = amt - self.get_amount_of(res)

                if shortfall > 0:
                    rate = self.conversion_rate(Resource.GOLD, res)
                    gold_amount = int(math.ceil(shortfall * rate))
                    total_gold += gold_amount
                    conversion['%s2%s' % (Resource.GOLD, res)] = gold_amount


        if self.get_amount_of(Resource.GOLD) < resource_levels[Resource.GOLD]:
            logger.debug('Not enough gold available for required resource levels.')
        elif total_gold == 0:
            if convert is not False:
                logger.debug('No need to exchange any resources')
            return True
        elif total_gold < self.get_amount_of(Resource.GOLD):
            if not convert:
                return True

            logger.debug('Total gold cost of conversion is %d' % total_gold)
            json = self._convert(**conversion)
            return json['code'] == EmrossWar.SUCCESS
        else:
            logger.debug('Unfortunately, we are lacking gold for the exchange')

        return False
