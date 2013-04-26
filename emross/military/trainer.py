from emross.api import EmrossWar
from emross.military.camp import Soldier
from emross.structures.buildings import Building
from emross.structures.construction import Construct
from emross.utility.task import FilterableCityTask, TaskType

import logging
logger = logging.getLogger(__name__)
import time

class Cavalry:
    def __init__(self, troop, quantity, *args, **kwargs):
        self.troop = troop
        self.quantity = quantity


class Trainer(FilterableCityTask):
    INTERVAL = 600

    def process(self, cavalries, *args, **kwargs):
        """
        Try to keep cities stocked up on the specified troop specifications (cavalries)
        """
        cities = self.cities(**kwargs)

        if len(cities) == 0:
            self.sleep(5)
            return False

        construction = self.bot.builder.task(Construct)
        delays = []
        for city in cities:
            if construction.structure_level(city, Building.BARRACKS) < 1:
                logger.info('There is no Barracks at castle "%s"' % city.name)
                continue

            delay = self.INTERVAL
            tasks = city.countdown_manager.get_tasks(task_type=TaskType.TRAIN)
            if len(tasks) > 0:
                delays.append(int(tasks[0]['secs'])-time.time())
                logger.info('Already training troops at castle "%s"' % city.name)
                continue

            troops, info = city.barracks.total_troops()
            camp_space = int(info['ret']['space'])

            for cavalry in cavalries:
                try:
                    if not city.barracks.can_train(cavalry.troop):
                        logger.info('Cannot train troop type %d at city "%s"' % (cavalry.troop, city.name))
                        continue

                    if cavalry.quantity > troops[cavalry.troop]:
                        desired = cavalry.quantity - troops[cavalry.troop]
                        logger.debug('Shortfall of %d troops of type %d at city "%s"' % (desired, cavalry.troop, city.name))

                        qty = 0
                        while city.resource_manager.meet_requirements(Soldier.cost(cavalry.troop, qty+1), convert=False) and qty < desired:
                            qty += 1

                        qty = min(qty, camp_space)
                        if qty > 0:
                            city.resource_manager.meet_requirements(Soldier.cost(cavalry.troop, qty), convert=True)
                            json = city.barracks.train_troops(cavalry.troop, qty)
                            if json['code'] == EmrossWar.SUCCESS:
                                delay = int(json['ret']['cdlist'][0]['secs'])
                                city.countdown_manager.add_tasks(json['ret']['cdlist'])
                                logger.info('Stop processing the rest of the cavalries list at city "%s"' % city.name)
                                break
                except KeyError:
                    pass

            delays.append(delay)

        if delays:
            secs = min(delays) / 2
            logger.info('Retry troop training in %d seconds' % secs)
            self.sleep(secs)
