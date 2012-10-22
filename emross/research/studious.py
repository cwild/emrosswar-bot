from emross.utility.task import Task, TaskType
from tech import Tech
import time

import logging
logger = logging.getLogger(__name__)

class Study(Task):
    STUDY_URL = 'game/study_api.php'
    STUDY_MOD_URL = 'game/study_mod_api.php'
    TASK_TYPE = TaskType.RESEARCH

    def __init__(self, bot):
        super(Study, self).__init__()
        self.bot = bot


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
        t = self.tech_levels(city)[tech-1]
        return t[1] if t[2] == 1 else -1

    def upgrade(self, city, tech, owner=0):
        """
        {'code': 0, 'ret': {'cdlist': [{'owner': 0, 'secs': 1557, 'cdtype': 2, 'id': 123456, 'target': 1}]}}
        """
        return self.bot.api.call(self.STUDY_MOD_URL, city=city.id, tech=tech, owner=owner)

    def process(self, tech, level):
        current_study = set()
        for city in self.bot.cities:
            tasks = city.countdown_manager.get_tasks(task_type=TaskType.RESEARCH)
            for task in tasks:
                current_study.add(task['target'])

        for city in self.bot.cities:
            if self.tech_level(city, tech) < level:
                tasks = city.countdown_manager.get_tasks(task_type=TaskType.RESEARCH)
                if len(tasks) == 0 and tech not in current_study \
                    and city.resource_manager.meet_requirements(Tech.cost(tech, level)):
                    ctdwn = self.upgrade(city, tech)
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
