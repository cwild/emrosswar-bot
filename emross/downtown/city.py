import math

import emross
from emross.api import EmrossWar
from emross.arena import CONSCRIPT_URL
from emross.arena.hero import Hero
from emross.arena.heroes import HeroManager
from emross.exceptions import (InsufficientHeroCommand,
    InsufficientSoldiers, NoHeroesAvailable)
from emross.military.barracks import Barracks
from emross.military.camp import Soldier
from emross.resources import Resource, ResourceManager
from emross.utility.base import EmrossBaseObject
from emross.utility.countdown import CountdownManager

from lib.cacheable import CacheableData
from lib import six


class City(EmrossBaseObject, CacheableData):
    GET_CITY_INFO = 'game/get_cityinfo_api.php'

    def __init__(self, bot, id, name, x, y):
        super(City, self).__init__(bot, time_to_live=60)
        self.id = id
        self.name = EmrossWar.safe_text(name)
        self.x = x
        self.y = y
        self.log.debug(six.u('Created new city: name="{name}", id={id}, x={x}, y={y}').format(\
                name=self.name, id=self.id, x=x, y=y)
        )

        self.barracks = Barracks(bot, self)
        self.hero_manager = HeroManager(bot, self)
        self.heroes = []

        self.resource_manager = ResourceManager(bot, city=self)
        self.countdown_manager = CountdownManager(bot, city=self)

    def __str__(self):
        return six.u('City("{0.name}", x={0.x}, y={0.y})').format(self)

    @emross.defer.inlineCallbacks
    def update(self):
        """Get castle info"""

        """
        {"code":0,"ret":{"city":
            [
                12,210,          # Free land
                3736203,5766504, # Gold
                4508554,5766504, # Food
                1110460,5766504, # Wood
                2275066,5766504, # Iron
                11433,12232,     # Population

                14, # Sawmill
                12, # Iron
                5,  # Gold
                29, # Farm
                20, # House
                25, # Barracks
                22, # Uni
                21, # Arena
                10, # Storage
                20, # Wall
                18, # Facility Center
                [{"id":11659,"itemid":166,"secs":532417}],0],"grade":53,"money":40}}
        """

        self.log.debug(six.u('Updating city "{0}"').format(self.name))
        json = yield self.bot.api.call(self.GET_CITY_INFO, city=self.id)
        userinfo = yield self.bot.userinfo

        userinfo['level'] = json['ret']['grade']
        userinfo['money'] = json['ret']['money']
        userinfo['pvp'] = json['ret']['pvp']

        emross.defer.returnValue(json['ret']['city'])


    @emross.defer.inlineCallbacks
    def get_active_buffs(self):
        """
        eg:
        [{'itemid': 196, 'secs': 3403, 'id': 413076}]
        """
        json = yield self.data
        emross.defer.returnValue(json[23])

    @emross.defer.inlineCallbacks
    def add_buff(self, buff):
        buffs = yield self.get_active_buffs()
        buffs.append(buff)

    @emross.defer.inlineCallbacks
    def get_gold_count(self):
        result = yield self.resource_manager.get_amounts_of(Resource.GOLD)
        emross.defer.returnValue(result)


    @emross.defer.inlineCallbacks
    def replenish_food(self, amount=None):
        self.log.debug('Replenishing food')
        if not amount:
            food, food_limit = yield self.resource_manager.get_amounts_of(Resource.FOOD)
            amount = food_limit - food

            if self.bot.minimum_food > 0:
                amount = self.bot.minimum_food - food
                if amount < 0:
                    self.log.debug('The current food levels exceed the minimum level specified')
                    emross.defer.returnValue(None)

                self.log.info('Replenishing food reserves by {0} to fulfill specified minimum of {1}.'.format(amount, self.bot.minimum_food))

        buy_gold = int(math.ceil(self.resource_manager.conversion_rate(Resource.GOLD, Resource.FOOD) * amount))

        available_gold = yield self.resource_manager.get_amount_of(Resource.GOLD)

        if buy_gold > available_gold:
            buy_gold = available_gold

        if buy_gold and buy_gold > 0:
            yield self.resource_manager.convert(Resource.GOLD, Resource.FOOD, buy_gold)


    @emross.defer.inlineCallbacks
    def create_army(self, threshold, heroes=[], mixed=False):
        """
        Return a dict of the various soldiers to include in this army.
        `threshold` can be a dict-like object or a list
        """
        if not heroes:
            _heroes = yield self.hero_manager.heroes
            heroes = _heroes.values()

        if not heroes:
            raise NoHeroesAvailable('Cannot find any available heroes at "{0}"'.format(self.name))

        army = {}

        max_carry = max([hero.stat(Hero.COMMAND) for hero in heroes])
        remaining_hero_command = max_carry

        try:
            iterable = threshold.iteritems()
        except AttributeError:
            iterable = threshold

        for soldier, qty in iterable:
            """
            If there are enough of a given soldier to send
            then add them to the army
            """
            utilised = army.get(soldier, 0)
            try:
                if qty is not Soldier.REMAINING and max_carry < qty:
                    if mixed:
                        raise InsufficientHeroCommand('With a mixed army, all troops must be sent')

                    continue

                available = self.barracks.available_units(soldier)
                use_remaining = False

                if qty is Soldier.REMAINING:
                    qty = min([available-utilised, remaining_hero_command])
                    use_remaining = qty>0

                    if use_remaining is False:
                        # We are not able to take any more of this troop
                        continue

                if use_remaining or available-utilised >= qty:
                    army[soldier] = utilised + qty
                    remaining_hero_command -= qty

                    if not mixed:
                        break

                elif mixed:
                    raise InsufficientSoldiers('Not enough specified troops')
            except (IndexError, ValueError):
                pass

        if army and mixed:
            self.log.debug(gettext('Total army size {0}').format(army))

            total = sum(army.values())
            if total > max_carry:
                raise InsufficientHeroCommand('This hero cannot command this many troops')

        if not army:
            raise InsufficientSoldiers('No soldiers were added to the army at "{0}"'.format(self.name))

        result = dict([('soldier_num{0}'.format(k), v) for k, v in army.iteritems()])
        emross.defer.returnValue(result)


    @emross.defer.inlineCallbacks
    def get_available_heroes(self, extra=1, stats=[Hero.LEVEL, Hero.EXPERIENCE], exclude=True):
        """
        Find the available heroes for this city
        """

        """
        {"hero":[
            {"id":13668,"gid":70,"p":56,"i":24,"c1":23,"f":50,"g":12,"c2":906,"fy":0,"s":0,"e":16,"w":3,"tw":3,"tl":0,"ex":141056,"te":257100,"np":0,"ni":0,"nc1":0,"nc2":150,"ns":0,"ncd":0,"pr":36000},
            {"id":12608,"gid":59,"p":36,"i":70,"c1":40,"f":50,"g":14,"c2":859,"fy":0,"s":0,"e":16,"w":1,"tw":12,"tl":2,"ex":405312,"te":1244364,"np":0,"ni":0,"nc1":0,"nc2":0,"ns":0,"ncd":0,"pr":42000},
            {"id":13048,"gid":83,"p":65,"i":20,"c1":41,"f":50,"g":13,"c2":819,"fy":0,"s":0,"e":16,"w":1,"tw":9,"tl":1,"ex":40897,"te":565620,"np":35,"ni":16,"nc1":35,"nc2":432,"ns":0,"ncd":0,"pr":39000},
            {"id":12939,"gid":60,"p":61,"i":21,"c1":26,"f":50,"g":13,"c2":836,"fy":0,"s":0,"e":16,"w":2,"tw":8,"tl":4,"ex":269883,"te":565620,"np":0,"ni":0,"nc1":0,"nc2":0,"ns":0,"ncd":0,"pr":39000},
            {"id":13460,"gid":22,"p":92,"i":24,"c1":46,"f":50,"g":13,"c2":987,"fy":0,"s":0,"e":16,"w":6,"tw":6,"tl":0,"ex":23574,"te":565620,"np":55,"ni":23,"nc1":45,"nc2":744,"ns":0,"ncd":0,"pr":39000},
            {"id":11969,"gid":10,"p":102,"i":22,"c1":46,"f":60,"g":15,"c2":1111,"fy":0,"s":0,"e":16,"w":2,"tw":69,"tl":9,"ex":1194745,"te":2737601,"np":100,"ni":25,"nc1":52,"nc2":1024,"ns":0,"ncd":0,"pr":45000},
            {"id":13616,"gid":72,"p":78,"i":17,"c1":23,"f":50,"g":12,"c2":933,"fy":0,"s":0,"e":16,"w":4,"tw":5,"tl":1,"ex":56470,"te":257100,"np":0,"ni":0,"nc1":0,"nc2":150,"ns":0,"ncd":0,"pr":36000}
            ]
        }
        """
        json = yield self.bot.api.call(CONSCRIPT_URL, city=self.id, action='gen_list', extra=extra)
        self.heroes[:] = []

        heroes = json['ret']['hero']
        heroes.sort(key = lambda val: [val.get(stat) for stat in stats])

        for data in heroes:
            try:
                if exclude and data['gid'] in getattr(self.bot.settings, 'exclude_heroes', ()):
                    continue
            except AttributeError:
                pass

            self.heroes.append(Hero(data))


    @emross.defer.inlineCallbacks
    def choose_hero(self, capacity=None,
        exclude_hero_ranks=[],
        **kwargs):
        """
        Which hero should we use?
        """
        _heroes = yield self.hero_manager.ordered_by_stats([Hero.COMMAND])
        heroes = [h for h in _heroes
                    if h.stat(Hero.VIGOR) > 0 and not h.stat(Hero.GUARDING)
                    and h.stat(Hero.STATE) == Hero.AVAILABLE
                    and h.client.get('rank') not in exclude_hero_ranks
                ]

        if not heroes:
            raise NoHeroesAvailable

        if not capacity:
            emross.defer.returnValue(heroes[0])

        for hero in heroes[::-1]:
            if hero.stat(Hero.COMMAND) >= capacity:
                emross.defer.returnValue(hero)

        raise InsufficientHeroCommand
