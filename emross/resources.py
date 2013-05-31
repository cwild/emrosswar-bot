import math

from emross.api import EmrossWar
from emross.exceptions import EmrossWarException
from emross.utility.base import EmrossBaseObject

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

class ResourceManager(EmrossBaseObject):
    LOCAL_MARKET_URL = 'game/local_market_api.php'

    def __init__(self, bot, city):
        super(ResourceManager, self).__init__(bot)
        self.city = city
        self._data = None

    @property
    def data(self):
        if self._data is None:
            """{"code":0,"ret":{"g2w":0.06,"g2f":0.13,"g2i":0.1,"w2g":17,"f2g":80,"i2g":11}}"""
            json = self.bot.api.call(self.LOCAL_MARKET_URL, city=self.city.id)
            self._data = json['ret']

        return self._data

    def conversion_rate(self, from_res, to_res):
        return self.data.get('{0}2{1}'.format(from_res, to_res))

    def convert(self, from_res, to_res, amount=0):
        cvr = '{0}2{1}'.format(from_res, to_res)
        conversion = {cvr: amount}
        self.log.debug('Convert {0} {1}'.format(cvr, amount))

        if amount:
            self._convert(**conversion)


    def _convert(self, **kwargs):
        self.log.debug('Exchanging resources {0} at "{1}"'.format(kwargs, self.city.name))
        json = self.bot.api.call(self.LOCAL_MARKET_URL, city=self.city.id, reso_put='giveput', **kwargs)

        if json['code'] == EmrossWar.SUCCESS:
            for res, amt in json['ret'].iteritems():
                self.log.debug('Setting {0} resource to {1} at "{2}"'.format(res, amt, self.city.name))
                self.set_amount_of(res, amt)

        return json

    def get_amounts_of(self, resource):
        offset = Resource.OFFSETS[resource]
        return self.city.data[offset:offset+2]

    def get_amount_of(self, resource, idx=0):
        return self.get_amounts_of(resource)[idx]

    def set_amount_of(self, resource, amount):
        self.city.data[Resource.OFFSETS[resource]] = amount

    def meet_requirements(self, resource_levels, convert=True, unbrick=False,
                            include_minimum_food=True, **kwargs):
        """
        Try to match the desired resource levels at the current city. Optionally,
        we can check to see if we can sell stashed gold bricks to meet these levels
        """
        conversion = {}
        total_gold = 0

        if include_minimum_food:
            resource_levels[Resource.FOOD] = self.bot.minimum_food + \
                                resource_levels.get(Resource.FOOD, 0)

        for res, amt in resource_levels.iteritems():
            if res != Resource.GOLD:
                shortfall = amt - self.get_amount_of(res)

                if shortfall > 0:
                    rate = self.conversion_rate(Resource.GOLD, res)
                    gold_amount = int(math.ceil(shortfall * rate))
                    total_gold += gold_amount
                    conversion['%s2%s' % (Resource.GOLD, res)] = gold_amount


        if self.get_amount_of(Resource.GOLD) < total_gold + resource_levels[Resource.GOLD]:
            if unbrick is False:
                self.log.debug('Not enough gold available for required resource levels.')
                return False
        elif total_gold == 0:
            self.log.debug('No need to exchange any resources')
            return True
        elif convert is False:
            self.log.debug('We could have met the desired resources if we had chosen to convert')
            return True

        if convert:
            should_convert = total_gold > 0

            if unbrick:
                gold_required = total_gold + resource_levels[Resource.GOLD] - \
                                self.get_amount_of(Resource.GOLD)

                if gold_required > 0:
                    self.log.info('We need to unbrick {0} {1} before converting'.format(\
                        gold_required, EmrossWar.LANG.get('COIN', 'gold')))

                    should_convert = self.bot.find_gold_for_city(self.city,
                                        gold_required, unbrick=True)

            if should_convert and conversion:
                self.log.debug('Total gold cost of conversion is {0}'.format(total_gold))
                json = self._convert(**conversion)
                return json['code'] == EmrossWar.SUCCESS

        self.log.debug('Target resource requirements not met')
        return False
