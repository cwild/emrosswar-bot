import math
from lib import six

import emross
from emross.api import EmrossWar
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
    @emross.defer.inlineCallbacks
    def data(self):
        if self._data is None:
            """{"code":0,"ret":{"g2w":0.06,"g2f":0.13,"g2i":0.1,"w2g":17,"f2g":80,"i2g":11}}"""
            json = yield self.bot.api.call(self.LOCAL_MARKET_URL, city=self.city.id)
            self._data = json['ret']

        emross.defer.returnValue(self._data)

    @emross.defer.inlineCallbacks
    def conversion_rate(self, from_res, to_res):
        data = yield self.data
        emross.defer.returnValue(data.get('{0}2{1}'.format(from_res, to_res)))

    @emross.defer.inlineCallbacks
    def convert(self, from_res, to_res, amount=0):
        cvr = '{0}2{1}'.format(from_res, to_res)
        conversion = {cvr: amount}
        self.log.debug('Convert {0} {1}'.format(cvr, amount))

        if amount:
            yield self._convert(**conversion)


    @emross.defer.inlineCallbacks
    def _convert(self, **kwargs):
        self.log.debug(six.u('Exchanging resources {0} at {1}').format(kwargs, self.city))
        json = yield self.bot.api.call(self.LOCAL_MARKET_URL, city=self.city.id, reso_put='giveput', **kwargs)

        if json['code'] == EmrossWar.SUCCESS:
            for res, amt in json['ret'].iteritems():
                self.log.debug(six.u('Setting {0} resource to {1} at {2}').format(res, amt, self.city))
                self.set_amount_of(res, amt)

        emross.defer.returnValue(json)

    @emross.defer.inlineCallbacks
    def get_amounts_of(self, resource):
        offset = Resource.OFFSETS[resource]
        data = yield self.city.data
        emross.defer.returnValue(data[offset:offset+2])

    @emross.defer.inlineCallbacks
    def get_amount_of(self, resource, idx=0):
        qty = yield self.get_amounts_of(resource)
        emross.defer.returnValue(qty[idx])

    def set_amount_of(self, resource, amount):
        self.city._data[Resource.OFFSETS[resource]] = amount

    def modify_amount_of(self, resource, amount):
        self.city._data[Resource.OFFSETS[resource]] += amount

    @emross.defer.inlineCallbacks
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
                current = yield self.get_amount_of(res)
                shortfall = amt - current

                if shortfall > 0:
                    rate = yield self.conversion_rate(Resource.GOLD, res)
                    gold_amount = int(math.ceil(shortfall * rate))
                    total_gold += gold_amount
                    conversion['%s2%s' % (Resource.GOLD, res)] = gold_amount


        current_gold = yield self.get_amount_of(Resource.GOLD)
        if current_gold < total_gold + resource_levels[Resource.GOLD]:
            if unbrick is False:
                self.log.debug('Not enough gold available for required resource levels.')
                emross.defer.returnValue(False)
        elif total_gold == 0:
            self.log.debug('No need to exchange any resources')
            emross.defer.returnValue(True)
        elif convert is False:
            self.log.debug('We could have met the desired resources if we had chosen to convert')
            emross.defer.returnValue(True)

        if convert:
            should_convert = total_gold > 0

            if unbrick:
                gold_required = total_gold + resource_levels[Resource.GOLD] - \
                                current_gold

                if gold_required > 0:
                    self.log.debug('We need to unbrick {0} {1} before converting'.format(\
                        gold_required, EmrossWar.LANG.get('COIN', 'gold')))

                    should_convert = yield self.bot.find_gold_for_city(self.city,
                                        gold_required, unbrick=True)

            if should_convert:
                # No need to convert resources. Looks like all we were doing is unbricking
                if not conversion:
                    emross.defer.returnValue(True)

                self.log.debug('Total gold cost of conversion is {0}'.format(total_gold))
                json = yield self._convert(**conversion)
                emross.defer.returnValue(json['code'] == EmrossWar.SUCCESS)

        self.log.debug('Target resource requirements not met')
        emross.defer.returnValue(False)
