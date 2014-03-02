import copy
import time

#Fix for python2.6, see http://bugs.python.org/issue1515
import types
def _deepcopy_method(x, memo): # Copy instance methods
    return type(x)(x.im_func, copy.deepcopy(x.im_self, memo), x.im_class)
copy._deepcopy_dispatch[types.MethodType] = _deepcopy_method


from emross import exceptions
from emross import mobs
from emross.api import EmrossWar
from emross.arena.hero import Hero
from emross.farming.base import BaseFarmer
from emross.military.barracks import Barracks
from emross.utility.calculator import WarCalculator


class EfficientFarmer(BaseFarmer):
    INTERVAL = 600

    DEFAULT_SCOUT_DEVIL_ARMY_TYPES = [
        mobs.DevilArmy.SIX_STAR
    ]

    NPC_RATING_ORDER = [
        mobs.DevilArmy.EIGHT_STAR,
        mobs.DevilArmy.SEVEN_STAR,
        mobs.DevilArmy.SIX_STAR,
        mobs.DevilArmy.FIVE_STAR,
        mobs.DevilArmy.FOUR_STAR,
        mobs.DevilArmy.THREE_STAR,
        mobs.DevilArmy.TWO_STAR,
        mobs.DevilArmy.ONE_STAR
    ]

    MOB_CALCULATIONS = {
        # Apparently, the NPC hero has no effect on the calculations
        'hero': None,
        'hero_base': 0,
        'troops': {},
        'ally': mobs.alliance,
        'soldier_data': mobs.Unit.soldier_data
    }

    def setup(self):
        super(EfficientFarmer, self).setup()
        self.calculator = WarCalculator(self.bot)

    def process_city_with_target(self, city, target):
        farming_troops = self.kwargs.get('farming_troops')

        if not farming_troops:
            raise exceptions.BotException('No farming troops have been defined')

        self.log.debug('Calculate attack for {0}'.format(target.report))
        data = copy.deepcopy(self.MOB_CALCULATIONS)
        report = target.report

        if not report['troops']:
            self.log.debug('Error with report {0}'.format(target.id))
            raise exceptions.TargetException('No troops found for the report at ({x}, {y})'.format(x=target.x, y=target.y))

        for troop, count in report['troops'].iteritems():
            try:
                idx = mobs.Unit.find(troop, target.rating)
                data['troops'][idx] = count
            except ValueError as e:
                raise exceptions.TargetException(e.message)

        npc_defense = self.calculator.defense(**data)
        npc_min_attack, npc_max_attack = self.calculator.attack(**data)

        self.log.debug('Calculations for {0}, defense={1}, min_attack={2}, max_attack={3}'.format(\
            report['troops'], npc_defense, npc_min_attack, npc_max_attack))

        heroes = []
        for hero in city.hero_manager.heroes.itervalues():

            if any([hero.stat(Hero.GUARDING),
                    hero.stat(Hero.VIGOR) == 0,
                    hero.stat(Hero.STATE) != Hero.AVAILABLE,
                    hero.client.get('rank') in self.kwargs.get('exclude_hero_ranks', []),
                    hero.client.get('rank') in self.kwargs.get('exclude_hero_ranks_by_rating', {}).get(target.rating, [])
                    ]):
                self.log.debug('Hero "{0}" is not available.'.format(hero))
                continue

            army = {}
            capable_army = False
            carry = hero.stat(Hero.COMMAND)

            for troop in farming_troops:

                count = 0
                available = city.barracks.available_units(troop)

                while not capable_army and carry > count < available:
                    count += 1
                    army[troop] = count

                    try:
                        defense = self.calculator.defense(hero, army)
                        min_attack, max_attack = self.calculator.attack(hero, army)
                    except ValueError as e:
                        raise exceptions.TargetException(e.message)

                    if defense > npc_max_attack and min_attack > npc_defense:
                        try:
                            city.create_army(army, heroes=[hero], mixed=True)
                            heroes.append((hero, army))
                            capable_army = True
                        except exceptions.BotException as e:
                            self.log.debug(e)
                            del army[troop]

                        break

                if troop not in army:
                    self.log.debug('Unable to include troop type {0}'.format(troop))
                    continue

                self.log.debug('{0} would send {1} ({3}) for {2}'.format(hero, army, \
                    report['troops'], 'enough' if capable_army else 'NOT enough!'))


        if not heroes:
            raise exceptions.NoHeroesAvailable('No heroes to lead an army')

        heroes.sort(key=lambda h: h[1])
        self.log.debug(heroes)

        hero, army = heroes[0]

        SOLDIER_DATA = getattr(EmrossWar, 'SOLDIER_{0}'.format(self.bot.userinfo.get('nationid', 1)))
        army_text = ', '.join(['{0}x{1}'.format(qty, SOLDIER_DATA[str(troop)].get('name', 'troop_{0}'.format(troop)))
                               for troop, qty in army.iteritems()])

        army = city.create_army(army, heroes=[hero], mixed=True)


        self.log.info('Sending calculated attack: [{0}/{1}] {2} from "{3}" with {4}'.format(\
            target.y, target.x, hero, city.name, army_text))

        # send troops to attack
        params = {
            'action': 'do_war',
            'attack_type': Barracks.ATTACK,
            'gen': hero.data['gid'],
            'area': target.y,
            'area_x': target.x
        }
        params.update(army)
        self.log.debug(params)

        json = city.barracks.confirm_and_do(params, sleep_confirm=(5,8), sleep_do=(1,3))

        roundtrip = params.get('travel_sec', 0) * 2
        self.concurrent_attacks.append(time.time() + roundtrip)

        if json['code'] == EmrossWar.SUCCESS:
            target.attack += 1
            hero.data[Hero.STATE] = Hero.WAR

    def sort_favourites(self, favs=[]):
        """
        Sort based on the ratings, as soldier_threshold always did.
        """
        ratings = self.kwargs.get('scout_devil_army_types', self.NPC_RATING_ORDER)
        fav_by_rating = {}

        for fav in favs:
            if fav.rating in ratings:
                fav_by_rating.setdefault(fav.rating, []).append(fav)


        favs[:] = []
        for rating in ratings:
            favs.extend(fav_by_rating.get(rating, []))

        return favs

    def target_troops_are_attackable(self, troops):
        enemy_troops = self.kwargs.get('enemy_troops')
        if enemy_troops:
            limits = dict([(name, {'count':qty}) for name, qty in enemy_troops])
            return self.bot.scout_mail.parser.is_attackable(troops, limits)
        return True

    def utilities(self, *args, **kwargs):
        self.bot.scout_map(
            targets=kwargs.get('scout_devil_army_types', self.DEFAULT_SCOUT_DEVIL_ARMY_TYPES),
            add_scout_report_func=self.target_troops_are_attackable,
            **kwargs
        )
        self.bot.clean_war_reports(**kwargs)

        if not self.bot.pvp and kwargs.get('allow_inventory_clearout', True):
            self.bot.clearout_inventory()

        cities = super(EfficientFarmer, self).cities(**self.kwargs)
        for city in cities:
            city.replenish_food()

        self.log.info(self.bot.total_wealth())
