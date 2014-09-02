from lib import six

from emross.api import EmrossWar
from emross.item import inventory
from emross.structures.buildings import Building
from emross.utility.task import FilterableCityTask, TaskType

class Construct(FilterableCityTask):
    CREATE_TASK_URL = 'game/building_create_task_api.php'
    EXTRA_SLOT_ITEMS = (inventory.BLESS_OF_BUILDING_I[0], inventory.BLESS_OF_BUILDING_II[0])
    MAX_BUILD_SLOTS = 3

    COUNTDOWN_ITEMS = [
        (inventory.FAST_BUILDING_I[0], 900),
        (inventory.FAST_BUILDING_II[0], 3600),
        (inventory.FAST_BUILDING_III[0], 3600*8)
    ]

    def setup(self):
        self.bot.events.subscribe('countdown.task.expired', self._expire_building)

    def _expire_building(self, event, task, *args, **kwargs):
        if task['cdtype'] == TaskType.BUILDING:
            event.city.expire()

    def upgrade(self, city, build_type):
        """
        {"code":0,"ret":{"cdlist":[{"id":1234567,"cdtype":1,"target":"5","owner":0,"secs":90}]}}
        """
        json = self.bot.api.call(self.CREATE_TASK_URL, city=city.id, build_type=build_type)
        name = EmrossWar.BUILDING[str(build_type)].get('name', 'BUILD_TYPE {0}'.format(build_type))
        if json['code'] == EmrossWar.SUCCESS:
            self.log.info(six.u('Started building "{0}" at {1}. Time until completion: {2} seconds').format(name, city, json['ret']['cdlist'][0]['secs']))
        else:
            self.log.debug(six.u('Failed to upgrade "{0}" at {1}').format(name, city))
        return json

    def downgrade(self, city, build_type):
        return self.bot.api.call(self.CREATE_TASK_URL, city=city.id, build_type=build_type, build_act='destroy')

    def structure_level(self, city, building):
        return city.data[Building.OFFSET[building]]

    def process(self, structure, level,
        use_scrolls=False,
        open_slots=False,
        *args, **kwargs):
        """
        Go through each city and see if we can build the desired building to the target level.
        """

        # We should continue
        result = True

        for city in self.cities(**kwargs):

            if city.data[0] == 0:
                self.log.debug(six.u('{0} is out of free land. Unable to build.').format(city))
                continue

            current_level = self.structure_level(city, structure)
            if current_level < level:
                tasks = city.countdown_manager.get_tasks(task_type=TaskType.BUILDING)

                buffs = city.data[23]
                capacity = 1 + len([b for b in buffs if b['itemid'] in self.EXTRA_SLOT_ITEMS])
                self.log.debug(six.u('Build capacity at {0} is {1}').format(city, capacity))

                current_build = dict([(int(t['target']), t) for t in tasks])

                if structure in current_build:
                    task = current_build[structure]
                    city.countdown_manager.use_gems_for_task(task, **kwargs)

                    if use_scrolls:
                        city.countdown_manager.use_items_for_task(task, self.COUNTDOWN_ITEMS)

                elif open_slots and self.MAX_BUILD_SLOTS > len(tasks) == capacity:
                    """
                    Not already building this structure at this city.
                    Slots are full but we could open more
                    """
                    build_buffs = self.bot.find_inventory_items(self.EXTRA_SLOT_ITEMS)

                    done = False
                    for sid, vals in build_buffs.iteritems():
                        for item_id, qty, price in vals:

                            self.log.info('Open another build slot by using a "{0}"'.format(EmrossWar.ITEM[str(sid)].get('name')))
                            json = self.bot.item_manager.use(city=city, id=item_id, num=1)

                            if json['code'] == EmrossWar.SUCCESS:
                                capacity += 1
                                # we should have a new buff which applies to all cities
                                for _city in self.bot.cities:
                                    _city.expire()
                                done = True
                                self.bot.inventory.adjust_item_stock(item_id=item_id, num=-1)
                                break

                        if done:
                            break

                if len(tasks) < capacity and structure not in current_build \
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
