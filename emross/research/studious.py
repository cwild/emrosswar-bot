from lib import six

from emross.api import EmrossWar
from emross.arena.hero import Hero
from emross.item import inventory
from emross.structures.buildings import Building
from emross.structures.construction import Construct
from emross.utility.controllable import Controllable
from emross.utility.task import FilterableCityTask, TaskType
from tech import Tech

from lib.cacheable import CacheableData


class Study(FilterableCityTask, Controllable):
    COMMAND = 'tech'
    STUDY_URL = 'game/study_api.php'
    STUDY_MOD_URL = 'game/study_mod_api.php'

    COUNTDOWN_ITEMS = [
        (inventory.FAST_RESEARCH_I[0], 900),
        (inventory.FAST_RESEARCH_II[0], 3600),
        (inventory.FAST_RESEARCH_III[0], 3600*8)
    ]

    def setup(self):
        self._cities = {}
        self.bot.events.subscribe('countdown.task.expired', self._expire_research)

    def _expire_research(self, event, task, *args, **kwargs):
        if task['cdtype'] == TaskType.RESEARCH:
            for techs in self._cities.itervalues():
                techs.expire()

    def action_levels(self, event, *args, **kwargs):
        """
        Find out what my tech levels are!
        """
        message = []

        for tid, data in EmrossWar.TECHNOLOGY.iteritems():
            for arg in args:
                if arg not in data['name'].lower():
                    continue

                message.append(u'{0}={1}'.format(data['name'], \
                    self.get_tech_level(int(tid))
                ))

        if message:
            self.chat.send_message(u', '.join(message), event=event)

    def tech_levels(self, city):
        def _updater(*args, **kwargs):
            self.log.debug(six.u('Find tech levels for {0}').format(city))
            return self.bot.api.call(*args, **kwargs)

        return self._cities.setdefault(city, CacheableData(
            update=_updater,
            method=self.STUDY_URL,
            city=city.id
        ))

    def tech_level(self, city, tech):
        """
        Given `city`, return the current level of the queried `tech`.

        [22, 0, 1, 15000, 15000, 15000, 15000, 19]
        tech, level, unlocked, food, wood, iron, gold, time_required
        """
        try:
            tech, level, unlocked = [t[:3] for t in self.tech_levels(city) if int(t[0]) == tech][0]
            return level if unlocked == 1 else -1
        except IndexError:
            return -1

    def get_tech_level(self, tech):
        construction = self.bot.builder.task(Construct)
        cities = sorted(self.bot.cities, reverse=True, key= lambda city:
            construction.structure_level(city, Building.UNIVERSITY)
        )
        return max(self.tech_level(cities[0], tech), 0)

    def upgrade(self, city, tech, owner=0):
        """
        {'code': 0, 'ret': {'cdlist': [{'owner': 0, 'secs': 1557, 'cdtype': 2, 'id': 123456, 'target': 1}]}}
        """
        json = self.bot.api.call(self.STUDY_MOD_URL, city=city.id, tech=tech, owner=owner)
        name = EmrossWar.TECHNOLOGY[str(tech)].get('name', 'TECH {0}'.format(tech))

        if json['code'] == EmrossWar.SUCCESS:
            self.log.info(six.u('Started research "{0}" at {1}. Time until completion: {2} seconds.').format(\
                name, city, json['ret']['cdlist'][0]['secs'])
            )
        else:
            self.log.debug(six.u('Failed to start "{0}" at {1}').format(name, city))

        return json

    def can_study(self, city, tech, level):
        try:
            return 0 <= self.tech_level(city, tech) < level
        except IndexError:
            self.log.debug(six.u('The university at {0} is not high enough to study tech {1} yet.').format(city, tech))
            return False

    def process(self, tech, level, university=1,
        use_hero=False, use_scrolls=False, ordered=False, *args, **kwargs):

        if self.get_tech_level(tech) == level:
            self.log.debug(six.u('Tech {0} is already at target level {1}').format(tech, level))
            return

        # Copy the cities so ordering doesn't affect the real order
        cities = list(self.cities(**kwargs))
        for city in cities:
            tasks = city.countdown_manager.get_tasks(task_type=TaskType.RESEARCH)
            for task in tasks:
                if tech == task['target']:
                    city.countdown_manager.use_gems_for_task(task, **kwargs)

                    if use_scrolls:
                        city.countdown_manager.use_items_for_task(task, self.COUNTDOWN_ITEMS)

                    # Already researching this tech
                    return

        construction = self.bot.builder.task(Construct)

        if ordered:
            # Descending order
            cities.sort(key = lambda city: construction.structure_level(city, Building.UNIVERSITY), reverse=True)
            self.log.debug(six.u('Ordered cities: {0}').format([(city.name, construction.structure_level(city, Building.UNIVERSITY)) for city in cities]))

        for city in cities:
            if construction.structure_level(city, Building.UNIVERSITY) < university:
                self.log.debug(six.u('The university at {0} does not meet the specified minimum of {1}').format(city, university))
                continue

            tasks = city.countdown_manager.get_tasks(task_type=TaskType.RESEARCH)
            if len(tasks):
                if tasks[0]['target'] == tech:
                    self.log.debug(six.u('{hero} is already researching {tech} at {city}').format(\
                        hero=city.hero_manager.heroes.get(tasks[0]['owner'], 'N/A'),
                        tech=EmrossWar.TECHNOLOGY[str(tasks[0]['target'])].get('name', '?'),
                        city=city))

                # Already a research in-progress at this city
                continue

            if not self.can_study(city, tech, level):
                continue

            owner = 0
            if use_hero:
                hero = city.hero_manager.highest_stat_hero(Hero.WISDOM)
                if not hero:
                    self.log.info('Unable to find any heroes suitable for use')
                    continue
                elif hero.stat(Hero.VIGOR) and hero.stat(Hero.STATE) == Hero.AVAILABLE:
                    owner = hero.data.get('id', 0)
                    self.log.info(six.u('{0} chosen to research {1} at {2}').format(hero,
                        EmrossWar.TECHNOLOGY[str(tech)].get('name', '?'),
                        city.name))
                else:
                    self.log.info('{0} needs to rest before starting research'.format(hero))
                    continue

            if city.resource_manager.meet_requirements(Tech.cost(tech, self.tech_level(city, tech)+1), **kwargs):
                ctdwn = self.upgrade(city, tech, owner)
                if ctdwn['code'] == EmrossWar.SUCCESS:
                    city.countdown_manager.add_tasks(ctdwn['ret']['cdlist'])
                    self.reschedule()
                    break


if __name__ == "__main__":
    from bot import bot
    s = Study(bot)

    bot.update()
    print s.tech_levels(bot.cities[0])
    print s.tech_level(bot.cities[0], Tech.ADVANCED_ARMOUR)
    print s.upgrade(city=bot.cities[0], tech=Tech.ADVANCED_ARMOUR, owner=0)
    print bot.cities[0].countdown_manager.get_countdown_info()
