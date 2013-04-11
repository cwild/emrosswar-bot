from emross.api import EmrossWar
from emross.item import inventory
from emross.utility.task import FilterableCityTask, TaskType

from buildings import Building

import logging
logger = logging.getLogger(__name__)

class Construct(FilterableCityTask):
    CREATE_TASK_URL = 'game/building_create_task_api.php'
    EXTRA_SLOT_ITEMS = (inventory.BLESS_OF_BUILDING_I[0], inventory.BLESS_OF_BUILDING_II[0])

    def upgrade(self, city, build_type):
        """
        {"code":0,"ret":{"cdlist":[{"id":1234567,"cdtype":1,"target":"5","owner":0,"secs":90}]}}
        """
        json = self.bot.api.call(self.__class__.CREATE_TASK_URL, city=city.id, build_type=build_type)
        name = EmrossWar.BUILDING[str(build_type)].get('name', 'BUILD_TYPE %d' % build_type)
        if json['code'] == EmrossWar.SUCCESS:
            logger.info('Started building "%s" at "%s". Time until completion: %d seconds.' % (name, city.name, json['ret']['cdlist'][0]['secs']))
        else:
            logger.debug('Failed to upgrade build_type "%s" at city "%s"' % (name, city.name))
        return json

    def downgrade(self, city, build_type):
        return self.bot.api.call(self.__class__.CREATE_TASK_URL, city=city.id, build_type=build_type, build_act='destroy')

    def structure_level(self, city, building):
        return city.data[Building.OFFSET[building]]

    def process(self, structure, level, *args, **kwargs):
        result = True

        for city in self.cities(**kwargs):

            if city.data[0] == 0:
                logger.info('City "%s" is out of free land. Unable to build.' % city.name)
                continue

            current_level = self.structure_level(city, structure)
            if current_level < level:
                tasks = city.countdown_manager.get_tasks(task_type=TaskType.BUILDING)

                buffs = city.data[23]
                capacity = 1 + len([b for b in buffs if b['itemid'] in self.EXTRA_SLOT_ITEMS])
                logger.debug('Build capacity at castle "%s" is %d' % (city.name, capacity))

                if len(tasks) < capacity and structure not in [t['target'] for t in tasks] \
                    and city.resource_manager.meet_requirements(Building.cost(structure, current_level+1), **kwargs):
                    ctdwn = self.upgrade(city, structure)
                    if ctdwn['code'] == EmrossWar.SUCCESS:
                        city.countdown_manager.add_tasks(ctdwn['ret']['cdlist'])
                else:
                    result = False

        return result


if __name__ == "__main__":
    from bot import bot
    st = Construct(bot)

    bot.update()
    print st.structure_level(bot.cities[0], Building.FARM)
    print st.upgrade(bot.cities[0], Building.FARM)
    print bot.cities[0].countdown_manager.get_countdown_info()
