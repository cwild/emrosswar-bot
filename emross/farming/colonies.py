import collections
import copy
import time

from emross import exceptions
from emross import mobs
from emross.api import EmrossWar
from emross.arena.hero import Hero
from emross.farming.base import BaseFarmer
from emross.farming.efficient import EfficientFarmer
from emross.favourites import Favourites, FAVOURITES_URL
from emross.military.barracks import Barracks
from emross.resources import Resource
from emross.utility.base import EmrossBaseObject
from emross.utility.calculator import WarCalculator
from emross.utility.controllable import Controllable
from emross.utility.task import TaskType

from lib.cacheable import CacheableData
from lib import six


REPORT_LIFETIME = 3600
REPORT_MAX_AGE = 86400

class ColonyFavourite(EmrossBaseObject):
    def __init__(self, data, bot):
        super(ColonyFavourite, self).__init__(bot)
        self._data = data
        self.id = data[0]
        self.x = data[1]
        self.y = data[2]
        self._setup()

    def __str__(self):
        return six.u('{0}: {1} ({2},{3})').format(
            EmrossWar.LANG.get('RESCOLONY', 'ResColony'),
            self.name, self.x, self.y)


    def _setup(self):
        try:
            colonies = self.bot.session.colonies
        except AttributeError:
            colonies = self.bot.session.colonies = collections.defaultdict(dict)

        def _fetch_node_data(*args, **kwargs):
            try:
                report = colonies[self.id]

                # If there is still some time remaining
                if (report['data'][3][3] or 0) > time.time():
                    return report

                elif report['time_queried'] + REPORT_MAX_AGE > time.time():
                    return report
            except KeyError:
                pass

            node = self.bot.world.get_point(self.x, self.y)
            node[3][3] = time.time() + int(node[3][3] or 0)

            result = {
                'time_queried': time.time(),
                'data': node
            }
            colonies[self.id].update(result)
            return result

        self._node = CacheableData(time_to_live=REPORT_LIFETIME,
                        update=_fetch_node_data)

        self._node.should_update = lambda slf: slf._data['data'][3][3] < time.time()


        def _fetch_mob_data(*args, **kwargs):
            try:
                report = colonies[self.id]
                if report['troops'] and time.time() < report['time_queried'] + REPORT_LIFETIME:
                    return report
            except KeyError:
                pass

            json = self.bot.api.call(FAVOURITES_URL, act='getfavnpc', fid=self.id)
            added_timestamp, msg = json['ret'].get('fav', (0, ''))
            result = {
                'time_added': added_timestamp,
                'troops': self.bot.scout_mail.parser.find_troops(msg)
            }
            colonies[self.id].update(result)
            return result

        self._mobs = CacheableData(time_to_live=REPORT_LIFETIME,
                        update=_fetch_mob_data)

    def attacked(self):
        self.log.debug('Target has been attacked. Mark cached data as expired')
        self._node.expire()
        self.node['data'][3][3] = 0
        self.node['time_queried'] = 0

    @property
    def node(self):
        return self._node.data

    @property
    def name(self):
        try:
            if self.is_special:
                return self.node['data'][3][4]
            return EmrossWar.LANG['RESOURCE_STYLE'][str(self.type)]['name']
        except (IndexError, KeyError):
            return 'Unknown({0})'.format(self.type)

    @property
    def is_special(self):
        try:
            return len(self.node['data'][3]) > 4
        except Exception as e:
            self.log.exception(e)
            raise e

    @property
    def mobs(self):
        return self._mobs.data.get('troops', {})

    @property
    def remaining_time(self):
        try:
            return int(self.node['data'][3][3] - time.time())
        except (IndexError, TypeError):
            return 0

    @property
    def type(self):
        return self._data[3]

"""
Setup so that when we add this type of favourite then
it will automatically be a ColonyFavourite.
"""
Favourites.TYPES[Favourites.COLONY] = ColonyFavourite


class ColonyFarmer(BaseFarmer, Controllable):
    COMMAND = 'colony'
    INTERVAL = 15

    FAVOURITES_TYPE = Favourites.COLONY
    OCCUPY_TASK = 6
    PER_CITY = 1

    COLONY_PREFERENCE = [
        Resource.FOOD,
        Resource.IRON,
        Resource.WOOD
    ]

    def setup(self):
        super(ColonyFarmer, self).setup()
        self.calculator = WarCalculator(self.bot)
        self._war_rooms = {}

        def check_cleared_tasks(event, task):
            if task['cdtype'] == self.OCCUPY_TASK:
                event.propagate = False
                event.city.countdown_manager.expire()
                self.reschedule()
        self.bot.events.subscribe('countdown.task.expired', check_cleared_tasks)

        self.special_event = False

    def action_special(self, event, *args, **kwargs):
        pass

    def is_target_attackable(self, target):
        """
        Check the War Rooms before checking the countdown tasks for each city.
        """
        cities = super(BaseFarmer, self).cities(**self.kwargs)

        if target.remaining_time > 0:
            self.log.debug(six.u('{0} already occupied').format(target))
            return False

        for city in cities:
            tasks = self._war_rooms.setdefault(city, CacheableData(
                time_to_live=self.INTERVAL-1,
                update=city.barracks.war_room
            ))

            coords = set([task[4]
                for task in tasks.data[0] if task[2] == Barracks.OCCUPY and
                    task[1] in (TaskType.ACTION, TaskType.RETURN)
            ])
            if '{0.x}/{0.y}'.format(target) in coords:
                self.log.debug(six.u('{0} is already being attacked').format(target))
                return False

        return True

    def process_city_with_target(self, city, target):
        """
        [278, 279, 104, [10309, 674259, '', '', 'Evil Santa`s Base', 'xmas.png']
        [
            271,
            90,
            103,
            [2262, 164930, [303030, 'koz33', 2, 76, 'THE DEAD', 1981, 4, 123, 0, 0, 266569],
                1931, 'Easter rabbit', 'rubby.png']
        ]
        [3][1] - resources per hour
        [3][3] - time remaining
        [3][4] - Special name
        [3][5] - Event image

        [64, 192, 103, [4829, 151948, '', '']]
        [x, y, type, [4829, hourly-rate, '', '']]
        """
        farming_troops = self.kwargs.get('farming_troops')
        if not farming_troops:
            raise exceptions.BotException('No farming troops have been defined')

        # Find the Occupy tasks
        tasks = [task for task in city.countdown_manager.get_tasks()
            if task['cdtype'] == self.OCCUPY_TASK or \
            (task['cdtype'] == TaskType.ACTION and task['target'] == Barracks.OCCUPY)
        ]
        if len(tasks) >= self.PER_CITY:
            raise exceptions.BotException(
                six.u('Unable to occupy anything further at {0}').format(city)
            )

        self.log.debug(six.u('Processing "{0}" ({x},{y}) at {1}').format(\
            EmrossWar.LANG['ColonyType'].get(str(target.type),
                'ColonyType({0})'.format(target.type)
            ),
            city, x=target.x, y=target.y
        ))

        data = copy.deepcopy(EfficientFarmer.MOB_CALCULATIONS)

        if not target.mobs:
            self.log.debug('Error with report {0}'.format(target.id))
            raise exceptions.TargetException('No troops found for the report at ({x}, {y})'.format(x=target.x, y=target.y))

        for troop, count in target.mobs.iteritems():
            try:
                idx = mobs.Unit.find(troop, target.type)
                data['troops'][idx] = count
            except ValueError as e:
                raise exceptions.TargetException(e.message)

        npc_defense = self.calculator.defense(**data)
        npc_min_attack, npc_max_attack = self.calculator.attack(**data)

        self.log.debug('Calculations for {0}, defense={1}, min_attack={2}, max_attack={3}'.format(\
            target.mobs, npc_defense, npc_min_attack, npc_max_attack))

        heroes = []
        for hero in city.hero_manager.heroes.itervalues():
            if (hero.stat(Hero.GUARDING)
                    or hero.stat(Hero.VIGOR) == 0
                    or hero.stat(Hero.STATE) != Hero.AVAILABLE
                    or hero.client.get('rank') in self.kwargs.get('exclude_hero_ranks', [])
                    or hero.client.get('rank') in self.kwargs.get('exclude_hero_ranks_by_colony', {}).get(target.type, [])
                    ):
                self.log.debug('Hero "{0}" is not available.'.format(hero))
                continue

            army = {}
            capable_army = False
            carry = hero.stat(Hero.COMMAND)

            for troop in farming_troops:

                count = 0
                available = city.barracks.available_units(troop)
                defense = 0

                while not capable_army and carry > count < available:
                    if count == 0 and npc_max_attack > defense:
                        # Use the defense from the last calculated troop wave
                        approx_qty = self.calculator.troops_to_defend_attack(troop, npc_max_attack-defense, hero)
                        self.log.debug('Use approximately {0} of troop {1}'.format(approx_qty, troop))
                        count = min(carry, available, approx_qty)
                    else:
                        count += 1

                    army[troop] = count

                    try:
                        defense = self.calculator.defense(hero, army)

                        """
                        Optimisation to reduce calls to `calculator.attack`
                        Each call takes around 1ms so this can be significant!
                        """
                        if defense < npc_max_attack:
                            continue

                        min_attack, max_attack = self.calculator.attack(hero, army)
                    except ValueError as e:
                        raise exceptions.TargetException(e.message)

                    if defense > npc_max_attack and min_attack > npc_defense:
                        try:
                            city.create_army(army, heroes=[hero], mixed=True)
                            heroes.append((hero, army))
                            capable_army = True
                        except exceptions.BotException as e:
                            defense = 0
                            self.log.debug(e)
                            del army[troop]

                        break

                if troop not in army:
                    self.log.debug('Unable to include troop type {0}'.format(troop))
                    continue

                self.log.debug(six.u('{0} would send {1} ({3}) for {2}').format(hero, army, \
                    target.mobs, 'enough' if capable_army else 'NOT enough!'))


        if not heroes:
            raise exceptions.NoHeroesAvailable('No heroes to lead an army')

        heroes.sort(key=lambda h: h[1])
        self.log.debug(heroes)

        hero, army = heroes[0]

        SOLDIER_DATA = getattr(EmrossWar, 'SOLDIER_{0}'.format(self.bot.userinfo.get('nationid', 1)))
        army_text = six.u(', ').join(['{0}x{1}'.format(qty, SOLDIER_DATA[str(troop)].get('name', 'troop_{0}'.format(troop)))
                               for troop, qty in army.iteritems()])

        army = city.create_army(army, heroes=[hero], mixed=True)


        self.log.info(six.u('Sending calculated attack: [{0}/{1}] {2} from {3} with {4}').format(\
            target.y, target.x, hero, city, army_text))

        # send troops to attack
        params = {
            'action': 'do_war',
            'attack_type': Barracks.OCCUPY,
            'gen': hero.data['gid'],
            'area': target.x,
            'area_x': target.y
        }
        params.update(army)
        self.log.debug(params)

        json = city.barracks.confirm_and_do(params, sleep_confirm=(5,8), sleep_do=(1,3))

        roundtrip = params.get('travel_sec', 0) * 2
        self.concurrent_attacks.append(time.time() + roundtrip)

        if json['code'] == EmrossWar.SUCCESS:
            hero.data[Hero.STATE] = Hero.WAR
            target.attacked()
            self._war_rooms[city].expire()

            # we now have an occupy job in progress for this castle
            city.countdown_manager.expire()

    def sort_targets(self, targets):
        colony_by_rating = {}

        for colony in targets:
            try:
                # Get the first letter => f/i/w
                resource = EmrossWar.LANG['RESOURCE_STYLE'][str(colony.type)]['ico'][0]

                colony_by_rating.setdefault(resource, []).append(colony)
            except (IndexError, KeyError) as e:
                self.log.error(e)


        colony_prefs = self.kwargs.get('colony_preference', self.COLONY_PREFERENCE)
        targets[:] = []
        for colony in colony_prefs:
            colonies = colony_by_rating.get(colony, [])

            # Negative remaining time, so least time first!
            if self.special_event:
                colonies.sort(key=lambda col: [col.is_special, col.type, -col.remaining_time], reverse=True)
            else:
                colonies.sort(key=lambda col: [col.type, -col.remaining_time], reverse=True)

            targets.extend(colonies)

        return targets
