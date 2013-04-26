from collections import deque
from copy import deepcopy

try:
    from HTMLParser import HTMLParser
except ImportError: #python3
    from html.parser import HTMLParser

import emross.arena
from emross.api import EmrossWar
from emross.arena.hero import Hero
from emross.exceptions import InsufficientHeroCommand, InsufficientSoldiers
from emross.military.camp import Soldier
from emross.scenario.scene import Scenario
from emross.utility.task import Task

import logging
logger = logging.getLogger(__name__)

import time

class ScenarioWalker(Task):
    INTERVAL = 10
    AUTO_HERO = -1

    def setup(self):
        self.html_parser = HTMLParser()
        self.scenario = None

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

        if self.scenario is None:
            self.scenario = Scenario(self.bot)

        json = self.scenario.list()

        if json['code'] != EmrossWar.SUCCESS:
            return resume

        if 'hasLottery' in json['ret'] and json['ret']['hasLottery']:
            self.scenario.finish()
            self.scenario = Scenario(self.bot)
            return resume

        if 'fb_label' in json['ret']:
            # Scenario in progress

            if scenario != int(json['ret']['fb_label']):
                logger.info('Already on a different scenario with {0} seconds remaining.'.format(json['ret']['remaining_time']))
                this.sleep(json['ret']['remaining_time'])
                return resume

            if int(json['ret']['finish']) == 1:
                self.scenario.finish()
                self.scenario = None
                return resume

            if not hasattr(self.scenario, 'armies'):
                self.scenario.armies = deepcopy(armies)
                generals = [int(gen) for gen in json['ret']['army_data'].keys()]
                city = self.find_city_with_heroes(generals, extra=None)
                logger.info('CITY {0}, GENERALS {1}'.format(city, generals))
                heroes = city.hero_manager.ordered_by_scored_stats(scoring, heroes=dict(
                        [(hero.data['id'], hero) for hero in city.hero_manager.heroes.itervalues() if hero.data['gid'] in generals]))

                logger.info('Our heroes are {0}'.format(heroes))

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
                logger.info('Out of turns in Scenarios. Try later.')
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
                        logger.debug('Minimum troop carry is {0}'.format(army_min_carry))
                        commands = [dict((h.data['gid'], h) for h in c.hero_manager.ordered_by_stats([Hero.COMMAND], exclude=generals)
                            if h.stat(Hero.COMMAND) >= carry)
                            for carry in army_min_carry]

                        logger.debug(commands)
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

                    logger.debug(champion_heroes_by_city)

                    highest = 0
                    for champion_city, champions in champion_heroes_by_city.iteritems():
                        city_score = sum([score for hero, score in champions])
                        if city_score > highest:
                            highest = city_score
                            city = champion_city

                    if city:
                        logger.info('Chosen city "{0}" with strongest heroes'.format(city.name))
                        generals = [hero.data['gid'] for hero, score in champion_heroes_by_city[city]]
                        logger.debug(generals)

                if city is not None:
                    city.barracks.camp_info()
                    heroes = dict([(h.data.get('gid'), h) for h in city.hero_manager.heroes.itervalues()])

                    for general in generals:
                        if heroes[general].stat(Hero.STATE) != Hero.AVAILABLE:
                            logger.info('Hero "{0}" is not available, try again in 5 minutes'.format(heroes[general]))
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
                            logger.debug('Started scenario %d' % scenario)
                            logger.info('Started scenario "%s" with %s' % \
                                (EmrossWar.SCENARIO_TEXT.map_name(scenario),
                                ','.join(EmrossWar.HERO[str(a['hero'])]['name'] for a in armies)
                                )
                            )
                            logger.debug('Wait {0} seconds before first attack'.format(initial_delay))
                            self.sleep(initial_delay)
                    except (InsufficientHeroCommand, InsufficientSoldiers) as e:
                        logger.warning(e)
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

        logger.info('Timed scenarios. Retry in %d seconds' % delay)
        self.sleep(delay)

        return False


    def find_city_with_heroes(self, gens, **kwargs):
        logger.info('Search to see which city has these heroes: %s' % gens)
        heroes = set(gens)
        for city in self.bot.cities:
            city.get_available_heroes(exclude=False, **kwargs)
            available = set([int(h.data.get('gid')) for h in city.heroes])
            if heroes.issubset(available):
                logger.info('%s has these heroes!' % city.name)
                return city

        logger.warning('Cannot find these generals in a single city.')
        return None


    def init_paths(self, info):
        """
        Look at the scenario paths which have been assigned.
        Remove any points which we have already successfully visited.
        """
        logger.info('Clean the hero paths to ensure we are ready to attack the next point.')
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
                    logger.info('Hero %s is at the start!' % hero)
                    break
                elif str(current['pos']) not in info['ret']['status']:
                    logger.info('Hero %s is at a point which is not on the chosen path' % hero)
                    break
                elif str(army['path'][0]) in info['ret']['status']:
                    node = army['path'][0]
                    logger.info('Already defeated point %d. We are safe here!' % node)

                    if node in visited and node is not current['pos']:
                        logger.debug('We need to return to node %d on our next move!' % node)
                        break
                    else:
                        node = army['path'].popleft()
                        logger.debug('Removed %d from path of hero %s' % (node,hero))
                        visited.add(node)
                else:
                    logger.debug('The next point on the path is our next target!')
                    break


    def process_paths(self, scenario):
        wait = []

        for army in self.scenario.armies:
            hero_name = EmrossWar.HERO[str(army['hero'])]['name']
            logger.info('Processing hero %s with path: %s' % (hero_name,army['path']))

            if len(army['path']) == 0:
                logger.info('No more points for hero "%s" to attack.' % hero_name)
                continue

            point = army['path'][0]
            if point == 0:
                logger.debug('Point is 0 so we do not intend on moving.')
                army['path'].popleft()
                continue

            point_name = EmrossWar.SCENARIO_TEXT.point_name(scenario, point)
            info = self.scenario.move(point)

            if info['code'] == Scenario.SCENARIO_FINISHED:
                logger.info('Scenario finished!')
                self.scenario.finish()
                self.scenario = None
                return

            if info['code'] == Scenario.SCENARIO_EXPIRED:
                logger.info('Scenario time limit has expired')
                self.scenario.finish()
                self.scenario = None
                return

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
                        logger.info('Troop losses for hero "%s": %s' % (hero_name,losses))

                        if int(war_result['aflag']) == 1:
                            logger.info('"%s" has moved to %s' % (hero_name,point_name))
                            logger.debug('Hero "%s" has moved to point %d' % (army['hero'],point))

                            resources = self.html_parser.unescape(war_result['resource'])
                            logger.info('Resources won: %s' % (resources or 'Nothing',))

                            army['path'].popleft()

                            if len(army['path']) is 0:
                                logger.info("%s has reached it's final destination, %s" % \
                                    (hero_name,point_name))
                                logger.debug('This hero has no further points to attack. Refresh scenario info after a one second delay')
                                wait.append(1)

                    except KeyError:
                        logger.info('No war report, we merely moved into position at point %d (%s)!' % \
                            (point,point_name))
                        if int(json['ret']['pos']) == point:
                            army['path'].popleft()


                    # We need to let our hero rest!
                    cd = int(json['ret']['cd'])
                    logger.info('%s has a cooldown of %d second(s).' % (hero_name,cd))
                    self.sleep(cd)

        if wait:
            logger.info('We need to wait for a hero to progress. Come back as soon as possible.')
            self.sleep(min(wait))


    def refill_soldiers(self, gen):
        """
        Refill a heroes army before war
        TODO: Check the containing castle has the desired troops for this
        """
        hero_name = EmrossWar.HERO[str(gen)]['name']
        logger.info('Restock troops for %s' % hero_name)
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
