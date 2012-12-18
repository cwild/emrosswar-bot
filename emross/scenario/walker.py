from collections import deque
from copy import deepcopy

try:
    from HTMLParser import HTMLParser
except ImportError: #python3
    from html.parser import HTMLParser

from emross.api import EmrossWar
from emross.exceptions import InsufficientHeroCommand, InsufficientSoldiers
from emross.scenario.scene import Scenario
from emross.utility.task import Task

import logging
logger = logging.getLogger(__name__)

import time

class ScenarioWalker(Task):
    INTERVAL = 10

    def setup(self):
        self.html_parser = HTMLParser()
        self.scenario = None

    def process(self, scenario, armies, times=[], resume=True, initial_delay=0.5, *args, **kwargs):
        if self.bot.pvp:
            self.sleep(86400)
            return True

        if self.scenario is None:
            self.scenario = Scenario(self.bot)

        if len(self.bot.cities) == 0:
            return resume

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
                logger.info('Already on a different scenario with %d seconds remaining.' % json['ret']['remaining_time'])
                this.sleep(json['ret']['remaining_time'])
                return resume

            if int(json['ret']['finish']) == 1:
                self.scenario.finish()
                self.scenario = None
                return resume

            if not hasattr(self.scenario, 'armies'):
                self.scenario.armies = deepcopy(armies)
                for army in self.scenario.armies:
                    army['path'] = deque(army['path'])

                # Clean the path (useful incase the scenario had already been started)
                self.init_paths(json)

            self.process_paths()
        else:
            # Not started yet
            if json['ret']['times'] == 0:
                logger.info('Out of turns in Scenarios. Try later.')
                if times:
                    self.can_start(times)
                else:
                    self.sleep(3600)
            elif self.can_start(times):
                generals = [v['hero'] for v in armies]
                city = self.find_city_with_heroes(gens=generals)

                if city is not None:
                    city.get_soldiers()
                    heroes = dict([(h.data.get('gid'), h) for h in city.heroes])

                    try:
                        gen_armies = [city.create_army(dict(a['troops']), heroes=[heroes[a['hero']]], mixed=True) for a in armies]

                        if self.scenario.start(city, scenario, armies):
                            # We have started, so let's get going on the next cycle
                            logger.info('Started scenario %d' % scenario)
                            logger.debug('Wait %f seconds before first attack' % (initial_delay,))
                            self.sleep(initial_delay)
                    except (InsufficientHeroCommand, InsufficientSoldiers):
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


    def find_city_with_heroes(self, gens):
        logger.info('Search to see which city has these heroes: %s' % gens)
        heroes = set(gens)
        for city in self.bot.cities:
            city.get_available_heroes(exclude=False)
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
                    logger.info('Hero %d is at the start!' % hero)
                    break
                elif str(current['pos']) not in info['ret']['status']:
                    logger.info('Hero %d is at a point which is not on the chosen path' % hero)
                    break
                elif str(army['path'][0]) in info['ret']['status']:
                    node = army['path'][0]
                    logger.info('Already defeated point %d. We are safe here!' % node)

                    if node in visited and node is not current['pos']:
                        logger.debug('We need to return to node %d on our next move!' % node)
                        break
                    else:
                        node = army['path'].popleft()
                        logger.debug('Removed %d from path of hero %d' % (node,hero))
                        visited.add(node)
                else:
                    logger.debug('The next point on the path is our next target!')
                    break


    def process_paths(self):
        wait = []

        for army in self.scenario.armies:
            if len(army['path']) == 0:
                logger.info('No more points for hero %d to attack.' % army['hero'])
                continue

            point = army['path'][0]
            if point == 0:
                logger.debug('Point is 0 so we do not intend on moving.')
                army['path'].popleft()
                continue

            info = self.scenario.move(point)

            if info['code'] == Scenario.SCENARIO_FINISHED:
                logger.info('Scenario finished!')
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
                    war_result = json['ret']['war_report']['war_result']

                    losses = self.html_parser.unescape(war_result['aarmy_loss'])
                    logger.info('Troop losses for hero %d: %s' % (army['hero'],losses))

                    if int(war_result['aflag']) == 1:
                        logger.info('Hero %d has moved to point %d' % (army['hero'],point))

                        resources = self.html_parser.unescape(war_result['resource'])
                        logger.info('Resources won: %s' % resources)
                        army['path'].popleft()

                    # We need to let our hero rest!
                    cd = int(json['ret']['cd'])
                    logger.info('Hero %d has a cooldown of %d second(s).' % (army['hero'],cd))
                    self.sleep(cd)

        if wait:
            logger.info('We need to wait for a hero to progress. Come back as soon as possible.')
            self.sleep(min(wait))


    def refill_soldiers(self, gen):
        """
        Refill a heroes army before war
        TODO: Check the containing castle has the desired troops for this
        """
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
