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
    MINIMUM_CHECK_PERIOD = 30

    def process(self, cavalries, *args, **kwargs):
        """
        Try to keep cities stocked up on the specified troop specifications (cavalries)
        """
        cities = self.cities(**kwargs)

        construction = self.bot.builder.task(Construct)
        delays = []
        for city in cities:
            if construction.structure_level(city, Building.BARRACKS) < 1:
                self.log.info('There is no Barracks at castle "{0}"'.format(city.name))
                continue

            delay = None
            tasks = city.countdown_manager.get_tasks(task_type=TaskType.TRAIN)
            if len(tasks) > 0:
                delays.append(int(tasks[0]['secs'])-time.time())
                self.log.info('Already training troops at castle "{0}"'.format(city.name))
                continue

            troops = city.barracks.total_troops()
            camp_space = int(city.barracks.data.get('space', 0))

            for cavalry in cavalries:
                try:
                    if not city.barracks.can_train(cavalry.troop):
                        self.log.info('Cannot train troop type {0} at city "{1}"'.format(cavalry.troop, city.name))
                        continue

                    if cavalry.quantity > troops[cavalry.troop]:
                        desired = cavalry.quantity - troops[cavalry.troop]
                        self.log.debug('Shortfall of {0} troops of type {1} at city "{2}"'.format(desired, cavalry.troop, city.name))

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
                                self.log.info('Stop processing the rest of the cavalries list at city "{0}"'.format(city.name))
                                break
                except KeyError:
                    pass

            if delay:
                delays.append(delay)

        if delays:
            secs = max(self.MINIMUM_CHECK_PERIOD, min(delays) / 2)
            self.log.info('Retry troop training in {0} seconds'.format(secs))
            self.sleep(secs)
