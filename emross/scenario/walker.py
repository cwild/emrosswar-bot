import logging
import time

from collections import deque
from copy import deepcopy

try:
    from HTMLParser import HTMLParser
except ImportError: #python3
    from html.parser import HTMLParser

from emross.api import EmrossWar
from emross.arena.hero import Hero
from emross.exceptions import InsufficientHeroCommand, InsufficientSoldiers
from emross.military.camp import Soldier
from emross.scenario.scene import Scenario
from emross.utility.controllable import Controllable
from emross.utility.task import Task

logger = logging.getLogger(__name__)


class ScenarioWalker(Task, Controllable):
    INTERVAL = 10
    AUTO_HERO = -1
    COMMAND = 'scenario'

    def setup(self):
        self.html_parser = HTMLParser()
        self.scenario = Scenario(self.bot)

    def action_status(self, **kwargs):
        """How are scenes looking?"""

        info = self.scenario.list()

        if 'fb_label' in info['ret']:
            self.chat.send_message('Scenario={0}, time left={1}'.format(\
                EmrossWar.SCENARIO_TEXT.map_name(info['ret']['fb_label']), \
                self.bot.human_friendly_time(info['ret']['remaining_time'])
            ))

            SOLDIER_DATA = getattr(EmrossWar, 'SOLDIER_{0}'.format(self.bot.userinfo['nationid']))

            for army in info['ret'].get('army_data', {}).itervalues():
                hero = EmrossWar.HERO[str(army['hero'])]['name']
                troops = ','.join(['{0}x{1}'.format(qty, \
                                SOLDIER_DATA[soldier]['name'])
                                for soldier, qty in army['soldier'].iteritems()])

                self.chat.send_message('"{0}" leads {1}.'.format(hero, troops))
        else:
            self.chat.send_message('Scenario status: remaining={0}, highest={1}, lottery={3}'.format(\
                info['ret']['times'], int(info['ret'].get('highest_fb',0))+1, \
                info['ret'].get('hasLottery',False))
            )

    def process(self, scenario, armies, times=[], resume=True,
        initial_delay=0.5, mode=Scenario.NORMAL_MODE,
        scoring=[
            (Hero.ATTACK, 1.4),
            (Hero.DEFENSE, 1.2),
            (Hero.WISDOM, 0.8),
            (Hero.COMMAND, 1)
            ],
        *args, **kwargs):

        if self.bot.pvp:
            self.sleep(86400)
            return True

        if len(self.bot.cities) == 0:
            return resume

        if self.bot.userinfo.get('status', 0) in [EmrossWar.TRUCE, EmrossWar.VACATION]:
            self.sleep(60)
            return True

        json = self.scenario.list()

        if json['code'] != EmrossWar.SUCCESS:
            return resume

        if json['ret'].get('hasLottery', False):
            self.scenario.finish()
            self.scenario = Scenario(self.bot)
            return resume

        if 'fb_label' in json['ret']:
            # Scenario in progress

            if scenario != int(json['ret']['fb_label']):
                self.log.info('Already on a different scenario with {0} seconds remaining.'.format(json['ret']['remaining_time']))
                self.sleep(json['ret']['remaining_time'])
                return resume

            if int(json['ret']['finish']) == 1:
                self.scenario.finish()
                self.scenario = Scenario(self.bot)
                return resume

            if not hasattr(self.scenario, 'armies'):
                self.scenario.armies = deepcopy(armies)
                generals = [int(gen) for gen in json['ret']['army_data'].keys()]
                city = self.find_city_with_heroes(generals, extra=None)
                self.log.info('City: "{0}", Heroes: "{1}"'.format(city.name, generals))
                heroes = city.hero_manager.ordered_by_scored_stats(scoring, heroes=dict(
                        [(hero.data['id'], hero) for hero in city.hero_manager.heroes.itervalues() if hero.data['gid'] in generals]))

                self.log.info('Our heroes are {0}'.format(heroes))

                for hero, army in zip(heroes, self.scenario.armies):
                    hero, score = hero
                    army['hero'] = hero.data['gid'] if army['hero'] == self.AUTO_HERO else army['hero']
                    army['path'] = deque(army['path'])

                # Clean the path (useful incase the scenario had already been started)
                self.init_paths(json)

            self.process_paths(scenario)
        else:
            # Not started yet
            if json['ret']['times'] == 0:
                self.log.info('Out of turns in Scenarios. Try later.')
                if times:
                    self.can_start(times)
                else:
                    self.sleep(3600)
            elif self.can_start(times):
                city = None
                find_heroes = len(armies)
                generals = [v['hero'] for v in armies if v['hero'] != self.AUTO_HERO]
                if generals:
                    city = self.find_city_with_heroes(gens=generals)

                cities = [city] if city else self.bot.cities

                # Auto-hero selection
                remaining = find_heroes - len(generals)
                if remaining:
                    army_min_carry = [sum(num for troop, num in a['troops']
                        if num != Soldier.REMAINING)
                        for a in armies[-remaining:]
                        ]

                    champion_heroes_by_city = {}

                    for c in cities:
                        self.log.debug('Minimum troop carry is {0}'.format(army_min_carry))
                        commands = [dict((h.data['gid'], h) for h in c.hero_manager.ordered_by_stats([Hero.COMMAND], exclude=generals)
                            if h.stat(Hero.COMMAND) >= carry)
                            for carry in army_min_carry]

                        self.log.debug(commands)
                        exclude = []
                        champion_heroes_by_city[c] = []
                        for command in commands:
                            scored = c.hero_manager.ordered_by_scored_stats(scoring, command, exclude)
                            try:
                                hero, score = scored[0]
                                exclude.append(hero.data['gid'])
                                champion_heroes_by_city[c].append(scored[0])
                            except IndexError:
                                pass

                    self.log.debug(champion_heroes_by_city)

                    highest = 0
                    for champion_city, champions in champion_heroes_by_city.iteritems():
                        city_score = sum([score for hero, score in champions])
                        if city_score > highest:
                            highest = city_score
                            city = champion_city

                    if city:
                        self.log.info('Chosen city "{0}" with strongest heroes'.format(city.name))
                        generals = [hero.data['gid'] for hero, score in champion_heroes_by_city[city]]
                        self.log.debug(generals)

                if city is not None:
                    city.barracks.camp_info()
                    heroes = dict([(h.data.get('gid'), h) for h in city.hero_manager.heroes.itervalues()])

                    for general in generals:
                        if heroes[general].stat(Hero.STATE) != Hero.AVAILABLE:
                            self.log.info('Hero "{0}" is not available, try again in 5 minutes'.format(heroes[general]))
                            self.sleep(300)
                            return resume

                    try:
                        gen_armies = [city.create_army(troops, heroes=[heroes[hero]], mixed=True)
                            for troops, hero in zip([a['troops'] for a in armies], generals)
                            ]

                        armies = [{'hero':hero, 'troops':[(s.replace('soldier_num',''), qty) for s, qty in troops.iteritems()]}
                                  for hero, troops in zip(generals, gen_armies)]

                        if self.scenario.start(city, scenario, armies, mode=mode):
                            # We have started, so let's get going on the next cycle
                            self.log.debug('Started scenario %d' % scenario)
                            self.log.info('Started scenario "%s" with %s' % \
                                (EmrossWar.SCENARIO_TEXT.map_name(scenario),
                                ','.join(EmrossWar.HERO[str(a['hero'])]['name'] for a in armies)
                                )
                            )
                            self.log.debug('Wait {0} seconds before first attack'.format(initial_delay))
                            self.sleep(initial_delay)
                    except (InsufficientHeroCommand, InsufficientSoldiers) as e:
                        self.log.warning(e)
                        self.sleep(900)
                        return resume
                else:
                    self.sleep(3600)

        return resume


    def can_start(self, times, start_time=None):
        if not times:
            return True

        start_time = start_time or time.time()
        begin = time.localtime(start_time)
        wait = []

        for ctm in times:
            try:
                ltm = time.localtime()
                if ctm == (ltm.tm_hour, ltm.tm_min):
                    return True
                else:
                    delta = (begin.tm_year, begin.tm_mon, begin.tm_mday, ctm[0], ctm[1], 0, begin.tm_wday, begin.tm_yday, begin.tm_isdst)
                    wait.append(time.mktime(delta))
            except TypeError:
                pass

        try:
            delay = min([w for w in wait if w > start_time]) - start_time
        except ValueError:
            delay = min(wait) - start_time + 86400

        self.log.info('Timed scenarios. Retry in %d seconds' % delay)
        self.sleep(delay)

        return False


    def find_city_with_heroes(self, gens, **kwargs):
        self.log.info('Search to see which city has these heroes: {0}'.format(gens))
        heroes = set(gens)
        for city in self.bot.cities:
            city.get_available_heroes(exclude=False, **kwargs)
            available = set([int(h.data.get('gid')) for h in city.heroes])
            if heroes.issubset(available):
                self.log.info('"{0}" has these heroes!'.format(city.name))
                return city

        self.log.warning('Cannot find these generals in a single city.')
        return None


    def init_paths(self, info):
        """
        Look at the scenario paths which have been assigned.
        Remove any points which we have already successfully visited.
        """
        self.log.info('Clean the hero paths to ensure we are ready to attack the next point.')
        army_data = info['ret']['army_data']

        for army in self.scenario.armies:
            hero = str(army['hero'])
            current = army_data[hero]
            current['pos'] = int(current['pos'])


            """
            We are trying to account for paths such as:
            [1, 2, 3, 2, 4, 5, 6, 7, 8, 7, 9]
            [0, 0, 0]
            []
            """
            visited = set()
            while army['path']:
                if current['pos'] == 0:
                    self.log.info('Hero "{0}" is at the start!'.format(hero))
                    break
                elif str(current['pos']) not in info['ret']['status']:
                    self.log.info('Hero "{0}" is at a point which is not on the chosen path'.format(hero))
                    break
                elif str(army['path'][0]) in info['ret']['status']:
                    node = army['path'][0]
                    self.log.info('Already defeated point %d. We are safe here!' % node)

                    if node in visited and node is not current['pos']:
                        self.log.debug('We need to return to node {0} on our next move!'.format(node))
                        break
                    else:
                        node = army['path'].popleft()
                        self.log.debug('Removed {0} from path of hero {1}'.format(node,hero))
                        visited.add(node)
                else:
                    self.log.debug('The next point on the path is our next target!')
                    break


    def process_paths(self, scenario):
        wait = []

        for army in self.scenario.armies:
            hero_name = EmrossWar.HERO[str(army['hero'])]['name']
            self.log.info('Processing hero "{0}" with path: {1}'.format(hero_name, army['path']))

            if len(army['path']) == 0:
                self.log.info('No more points for hero "{0}" to attack.'.format(hero_name))
                continue

            point = army['path'][0]
            if point == 0:
                self.log.debug('Point is 0 so we do not intend on moving.')
                army['path'].popleft()
                continue

            point_name = EmrossWar.SCENARIO_TEXT.point_name(scenario, point)
            info = self.scenario.move(point)

            if info['code'] == Scenario.SCENARIO_FINISHED:
                self.log.info('Scenario finished!')
                self.scenario.finish()
                self.scenario = Scenario(self.bot)
                return

            if info['code'] == Scenario.SCENARIO_EXPIRED:
                self.log.info('Scenario time limit has expired')
                self.scenario.finish()
                self.scenario = Scenario(self.bot)
                return

            if info['code'] == Scenario.SCENARIO_OCCUPIED_ALREADY:
                wait.append(1)
                continue

            hero_war_data = info['ret']['soldier'][str(army['hero'])]

            if hero_war_data['cd'] > 0:
                wait.append(hero_war_data['cd'])
                continue

            topup = hero_war_data['add_soldier'] == 1
            if not topup or (topup and self.refill_soldiers(army['hero'])):
                json = self.scenario.attack(army['hero'], point)

                if json['code'] == EmrossWar.SUCCESS:
                    try:
                        war_result = json['ret']['war_report']['war_result']

                        losses = self.html_parser.unescape(war_result['aarmy_loss'])
                        self.log.info('Troop losses for hero "{0}": {1}'.format(hero_name,losses))

                        if int(war_result['aflag']) == 1:
                            self.log.info('"{0}" has moved to "{1}"'.format(hero_name,point_name))
                            self.log.debug('Hero "{0}" has moved to point {1}'.format(army['hero'],point))

                            resources = self.html_parser.unescape(war_result['resource'])
                            self.log.info(u'Resources won: {0}'.format(resources or 'Nothing'))

                            army['path'].popleft()

                            if len(army['path']) is 0:
                                self.log.info('''"{0}" has reached it's final destination, {1}'''.format(hero_name,
                                                                                                         point_name))
                                self.log.debug('This hero has no further points to attack. Refresh scenario info after a one second delay')
                                wait.append(1)

                    except KeyError:
                        self.log.info('No war report, we merely moved into position at point {0} ("{1}")!'.format(point,
                                                                                                              point_name))
                        if int(json['ret']['pos']) == point:
                            army['path'].popleft()


                    # We need to let our hero rest!
                    cd = int(json['ret']['cd'])
                    self.log.info('"{0}" has a cooldown of {1} second(s).'.format(hero_name,cd))
                    self.sleep(cd)

        if wait:
            self.log.info('We need to wait for a hero to progress. Come back as soon as possible.')
            self.sleep(min(wait))


    def refill_soldiers(self, gen):
        """
        Refill a heroes army before war
        TODO: Check the containing castle has the desired troops for this
        """
        hero_name = EmrossWar.HERO[str(gen)]['name']
        self.log.info('Restock troops for "{0}"'.format(hero_name))
        json = self.scenario.restock(gen)
        return json['code'] == EmrossWar.SUCCESS



if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    walker = ScenarioWalker(None)

    now = time.localtime()
    daybreak = (now.tm_year, now.tm_mon, now.tm_mday, 17, 30, 0, now.tm_wday, now.tm_yday, now.tm_isdst)

    print time.mktime(now), now
    print time.mktime(daybreak), daybreak

    print walker.can_start([], time.mktime(daybreak))
    print walker.can_start([(2,30), (17,15), (23,30)], time.mktime(daybreak))

    logger.info(EmrossWar.SCENARIO_TEXT.map_name(Scenario.ROSTER_BOG))
    logger.info(EmrossWar.SCENARIO_TEXT.point_name(Scenario.ROSTER_BOG, 1))
