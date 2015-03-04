import math

from lib import six

from emross.api import EmrossWar
from emross.military.barracks import Barracks
from emross.military.camp import Soldier
from emross.resources import Resource
from emross.utility.task import Task, TaskType
from emross.world import World


class CastleBuilder(Task):
    INTERVAL = 60

    EXPAND_EVERY = 15
    INITIAL_SLOTS = 2
    NAMING_SCHEME = '{nickname} {number}'
    PATIENT = True
    TAKE_RESOURCES = True

    def setup(self):
        def check_cleared_tasks(event, task):
            if task['cdtype'] == TaskType.ACTION and task['target'] == Barracks.BUILD:
                event.propagate = False
                self.bot.expire()
        self.bot.events.subscribe('countdown.task.expired', check_cleared_tasks)

    def find_closest_free_land(self, city):
        nodes = self.bot.world.get_page(city.x, city.y)['map']
        free_land = [node for node in nodes if node[2] == World.FREE_LAND]
        self.log.debug('Free land: {0}'.format(free_land))

        nx, ny = city.x, city.y
        max_x, max_y = self.bot.world.map_size()

        free_land.sort(key=lambda land: math.sqrt(
                min(abs(land[0]-nx), max_x-abs(land[0]-nx))**2
                + min( abs(land[1]-ny), max_y-abs(land[1]-ny) )**2
            )
        )
        self.log.debug('Free land (closest first): {0}'.format(free_land))
        return free_land

    def process(self, naming_scheme=NAMING_SCHEME, patient=PATIENT,
                take_resources=TAKE_RESOURCES,
                *args, **kwargs):

        if self.bot.pvp:
            return

        level = self.bot._data.get('level') or self.bot.userinfo.get('level')
        permitted = self.INITIAL_SLOTS + (level / self.EXPAND_EVERY)

        # cdtype=4 (TaskType.ACTION), target=5 (build)
        in_progress = sum([
            len([t for t in city.countdown_manager.get_tasks(TaskType.ACTION)
                    if t['target'] == Barracks.BUILD
            ]) for city in self.bot.cities
        ])
        self.log.debug('{0} castle builds in progress'.format(in_progress))

        remaining = permitted - len(self.bot.cities) - in_progress
        self.log.debug('Remaining castles to build: {0}'.format(remaining))

        # Where should we start counting from?
        cur = 1 + len(self.bot.cities) + in_progress
        for i in xrange(cur, cur+remaining):
            # Find city with Lonufal

            city = None
            for c in self.bot.cities:
                if c.barracks.available_units(Soldier.LONUFAL) > 0:
                    city = c
                    break

            if not city:
                self.log.debug('No city is currently able to initiate another castle build')
                return

            self.log.debug(six.u('Build from castle: "{0}"').format(city.name))

            proposed_name = naming_scheme.format(
                                nickname=self.bot.userinfo.get('nick'),
                                number=i
                            )

            self.log.debug(six.u('Proposed castle name: "{0}"').format(
                proposed_name
            ))

            try:
                free_land = self.find_closest_free_land(city, **kwargs)
                area_x, area_y = free_land.pop(0)[:2]
            except IndexError as e:
                self.log.debug(e)
                return

            params = {
                'action': 'do_war',
                'attack_type': Barracks.BUILD,

                # Again, backwards...
                'area': area_x,
                'area_x': area_y,

                'info': proposed_name,
            }

            json = city.barracks.action_confirm(params)

            costs = {
                Resource.FOOD: json['ret']['cost_food'],
                Resource.WOOD: json['ret']['cost_wood'],
                Resource.IRON: json['ret']['cost_iron'],
                Resource.GOLD: json['ret']['cost_gold'],
            }

            # How many resources should we take to the new castle?
            resources = {}
            if take_resources:
                remaining = json['ret']['carry'] - sum(costs.values())
                resources[Resource.GOLD] = remaining

                if not city.resource_manager.meet_requirements(resources.copy(), **kwargs):
                    return


            params.update({
                'action': 'war_task',
                'take_num': json['ret']['carry'],
                'travel_sec': json['ret']['travel_sec'],
                'distance': json['ret']['distance'],
                'action_rices': costs.get(Resource.FOOD, 0),
                'action_woods': costs.get(Resource.WOOD, 0),
                'action_irons': costs.get(Resource.IRON, 0),
                'action_golds': costs.get(Resource.GOLD, 0),
                'rices': resources.get(Resource.FOOD, 0),
                'woods': resources.get(Resource.WOOD, 0),
                'irons': resources.get(Resource.IRON, 0),
                'golds': resources.get(Resource.GOLD, 0),
            })

            json = city.barracks.action_do(params, alternative_costs=costs)

            if json['code'] != EmrossWar.SUCCESS:
                return

            self.log.info('Castle "{0}" build under way at x={1}, y={2}'.format(
                proposed_name, area_x, area_y
            ))

            city.barracks.expire()

            if patient:
                self.sleep(int(json['ret']['cd'][0]['secs']))
                city.countdown_manager.add_tasks(json['ret']['cd'])
                return
