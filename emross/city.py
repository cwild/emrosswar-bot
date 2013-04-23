import math
import time

import logging
logger = logging.getLogger(__name__)

from emross.api import EmrossWar
from emross.arena.hero import Hero
from emross.arena.heroes import HeroManager
from emross.exceptions import (InsufficientHeroCommand,
    InsufficientSoldiers, NoHeroesAvailable)
from emross.military.barracks import Barracks
from emross.military.camp import Soldier
from emross.resources import Resource, ResourceManager
from emross.structures.buildings import Building
from emross.structures.construction import Construct
from emross.utility.countdown import CountdownManager

import settings

class City:
    GET_CITY_INFO = 'game/get_cityinfo_api.php'

    def __init__(self, bot, id, name, x, y):
        self.bot = bot
        self.id = id
        self.name = name.encode('utf-8')
        self.x = x
        self.y = y
        self._data = []

        self.barracks = Barracks(self.bot, self)
        self.hero_manager = HeroManager(bot, self)
        self.heroes = []

        self.resource_manager = ResourceManager(bot, city=self)
        self.countdown_manager = CountdownManager(bot, city=self)
        self.next_hero_recruit = time.time()


    @property
    def data(self):
        if not self._data:
            self.update()
        return self._data


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

        logger.info('Updating city "%s"' % self.name)
        json = self.bot.api.call(self.GET_CITY_INFO, city = self.id)
        self._data[:] = json['ret']['city']


    def get_gold_count(self):
        return self.resource_manager.get_amounts_of(Resource.GOLD)


    def replenish_food(self, amount = None):
        logger.info('Replenishing food')
        if not amount:
            food, food_limit = self.resource_manager.get_amounts_of(Resource.FOOD)
            amount = food_limit - food

            try:
                amount = settings.minimum_food - food
                if amount < 0:
                    logger.debug('The current food levels exceed the minimum level specified')
                    return

                logger.info('Replenishing food reserves by %d to fulfill specified minimum of %d.' % (amount,settings.minimum_food))
            except AttributeError:
                pass

        buy_gold = int(math.ceil(self.resource_manager.conversion_rate(Resource.GOLD, Resource.FOOD) * amount))

        available_gold = self.resource_manager.get_amount_of(Resource.GOLD)

        if buy_gold > available_gold:
            buy_gold = available_gold

        if buy_gold and buy_gold > 0:
            self.resource_manager.convert(Resource.GOLD, Resource.FOOD, buy_gold)



    def create_army(self, threshold, deduct=True, heroes=[], mixed=False):
        """
        Return a dict of the various soldiers to include in this army.
        `threshold` can be a dict-like object or a list
        """
        heroes = heroes or self.heroes
        if len(heroes) == 0:
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
            try:
                if qty is not Soldier.REMAINING and max_carry < qty:
                    if mixed:
                        raise InsufficientHeroCommand('With a mixed army, all troops must be sent')

                    continue

                soldiers = [s for s in self.barracks.soldiers if s[0] == soldier][0]
                use_remaining = False

                if qty is Soldier.REMAINING:
                    qty = min([soldiers[1], remaining_hero_command])
                    use_remaining = qty>0

                    if use_remaining is False:
                        # We are not able to take any more of this troop
                        continue

                if use_remaining or soldiers[1] >= qty:
                    try:
                        army['soldier_num%d' % soldier] += qty
                    except KeyError:
                        army['soldier_num%d' % soldier] = qty

                    remaining_hero_command -= qty
                    """
                    Update soldier cache
                    """
                    if deduct:
                        soldiers[1] -= qty

                    if not mixed:
                        break

                elif mixed:
                    raise InsufficientSoldiers('Not enough specified troops')
            except (IndexError, ValueError):
                pass

        if army and mixed:
            total = sum([v for v in army.itervalues()])
            if total > max_carry:
                raise InsufficientHeroCommand('This hero cannot command this many troops')

        if not army:
            raise InsufficientSoldiers('No soldiers were added to the army')

        return army


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
        json = self.bot.api.call(settings.get_heroes, city=self.id, action='gen_list', extra=extra)
        self.heroes[:] = []

        heroes = json['ret']['hero']
        heroes.sort(key = lambda val: [val.get(stat) for stat in stats])

        for data in heroes:
            try:
                if exclude and data['gid'] in settings.exclude_heroes:
                    continue
            except AttributeError:
                pass

            self.heroes.append(Hero(data))


    def choose_hero(self, capacity = None):
        """
        Which hero should we use?
        """

        hero = None

        try:
            if capacity:
                for h in self.heroes:
                    if h.data.get(Hero.COMMAND) >= capacity:
                        hero = h
                        break

                self.heroes.remove(hero)
            else:
                hero = self.heroes.pop(0)
        except ValueError:
            pass

        return hero

    def recruit_hero(self):
        if not settings.enable_recruit:
            return

        if time.time() < self.next_hero_recruit:
            return

        st = Construct(self.bot)
        if st.structure_level(self, Building.ARENA) < 1:
            return

        logger.info('Check for heroes at the bar in "%s"' % self.name)
        json = self.bot.api.call(settings.hero_conscribe, city=self.id)


        if 'refresh' in json['ret']:
            logger.info('We have to wait before we can do this. Timer: %d' % json['ret']['refresh'])
            self.next_hero_recruit = time.time() + int(json['ret']['refresh'])
        else:
            logger.info('Try buying a drink')
            json = self.bot.api.call(settings.hero_conscribe, city=self.id, action='pub_process')

            if json['code'] == EmrossWar.REACHED_HERO_LIMIT:
                logger.info('Hero limit has been reached for this castle.')
                return


            if json['code'] == EmrossWar.INSUFFICIENT_GOLD:
                logger.info('Insufficient gold to buy a drink!')
                return
            else:
                self.next_hero_recruit = time.time() + int(json['ret']['refresh'])


            if 'hero' in json['ret'] and json['ret']['hero']['gid'] in settings.recruit_heroes:
                logger.info('Found a hero we are looking for: %d' % json['ret']['hero']['gid'])
                json = self.bot.api.call(settings.hero_conscribe, city=self.id, action='hire_process')

                if json['code'] == EmrossWar.SUCCESS:
                    logger.info('Hero recruited!')
                else:
                    logger.info('Could not recruit hero.')
