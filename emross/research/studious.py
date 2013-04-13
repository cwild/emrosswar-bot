import logging
import time

from emross.api import EmrossWar
from emross.arena.hero import Hero
from emross.structures.buildings import Building
from emross.structures.construction import Construct
from emross.utility.task import FilterableCityTask, TaskType
from tech import Tech

logger = logging.getLogger(__name__)

class Study(FilterableCityTask):
    STUDY_URL = 'game/study_api.php'
    STUDY_MOD_URL = 'game/study_mod_api.php'

    def tech_levels(self, city):
        logger.info('Find tech levels for this city, %s' % city.name)
        try:
            if time.time() < self._data[0]:
                logger.debug('Using cached data: %s' % self._data[1])
                return self._data[1]
            else:
                raise ValueError
        except (AttributeError, ValueError), e:
            self._data = (time.time()+10, self.bot.api.call(self.STUDY_URL, city=city.id)['ret'])

        return self._data[1]

    def tech_level(self, city, tech):
        tech, level, unlocked = self.tech_levels(city)[tech-1]
        return level if unlocked == 1 else -1

    def upgrade(self, city, tech, owner=0):
        """
        {'code': 0, 'ret': {'cdlist': [{'owner': 0, 'secs': 1557, 'cdtype': 2, 'id': 123456, 'target': 1}]}}
        """
        json = self.bot.api.call(self.STUDY_MOD_URL, city=city.id, tech=tech, owner=owner)
        name = EmrossWar.TECHNOLOGY[str(tech)].get('name', 'TECH %d' % tech)
        if json['code'] == EmrossWar.SUCCESS:
            logger.info('Started research "%s" at "%s". Time until completion: %d seconds.' % (name, city.name, json['ret']['cdlist'][0]['secs']))
        else:
            logger.debug('Failed to start "%s" at city "%s"' % (name, city.name))
        return json

    def can_study(self, city, tech, level):
        try:
            return 0 <= self.tech_level(city, tech) < level
        except IndexError:
            logger.debug('The university at "%s" is not high enough to study tech %d yet.' % (city.name, tech))
            return False

    def process(self, tech, level, university=1, use_hero=False, *args, **kwargs):
        cities = self.cities(**kwargs)
        current_study = set()
        for city in cities:
            tasks = city.countdown_manager.get_tasks(task_type=TaskType.RESEARCH)
            for task in tasks:
                current_study.add(task['target'])

        if tech in current_study:
            return

        construction = self.bot.builder.task(Construct)
        for city in cities:
            if construction.structure_level(city, Building.UNIVERSITY) < university:
                logger.info('The university at city "%s" does not meet the specified minimum of %d' % (city.name, university))
                continue

            tasks = city.countdown_manager.get_tasks(task_type=TaskType.RESEARCH)
            if len(tasks):
                logger.debug('{hero} is already researching {tech} at {city}'.format(\
                    hero=city.hero_manager.heroes.get(tasks[0]['owner'], 'N/A'),
                    tech=EmrossWar.TECHNOLOGY[str(tasks[0]['target'])].get('name', '?'),
                    city=city.name))
                continue

            owner = 0
            if use_hero:
                hero = city.hero_manager.highest_stat_hero(Hero.WISDOM)
                if hero.stat(Hero.VIGOR) and hero.stat(Hero.STATE) == Hero.AVAILABLE:
                    owner = hero.data.get('gid', 0)
                    logger.info('{0} chosen to research {1} at {2}'.format(hero,
                        EmrossWar.TECHNOLOGY[str(tech)].get('name', '?'),
                        city.name))
                else:
                    logger.info('{0} needs to rest before starting research'.format(hero))
                    continue

            if self.can_study(city, tech, level) and \
                city.resource_manager.meet_requirements(Tech.cost(tech, self.tech_level(city, tech)+1), **kwargs):
                    ctdwn = self.upgrade(city, tech, owner)
                    if ctdwn['code'] == EmrossWar.SUCCESS:
                        city.countdown_manager.add_tasks(ctdwn['ret']['cdlist'])
                        break


if __name__ == "__main__":
    from bot import bot
    s = Study(bot)

    bot.update()
    print s.tech_levels(bot.cities[0])
    print s.tech_level(bot.cities[0], Tech.ADVANCED_ARMOUR)
    print s.upgrade(city=bot.cities[0], tech=Tech.ADVANCED_ARMOUR, owner=0)
    print bot.cities[0].countdown_manager.get_countdown_info()
