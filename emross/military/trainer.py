from emross.api import EmrossWar
from emross.military.camp import Soldier
from emross.utility.task import Task, TaskType

import logging
logger = logging.getLogger(__name__)
import time

class Cavalry:
    def __init__(self, troop, quantity, *args, **kwargs):
        self.troop = troop
        self.quantity = quantity


class Trainer(Task):
    INTERVAL = 600

    def process(self, cavalries, city_names=None, *args, **kwargs):
        """
        Try to keep cities stocked up on the specified troop specifications (cavalries)
        """
        if self.bot.pvp or not city_names:
            cities = self.bot.cities
        else:
            cities = [city for city in self.bot.cities if city.name in city_names]

        delay = []

        for city in cities:
            tasks = city.countdown_manager.get_tasks(task_type=TaskType.TRAIN)
            if len(tasks) > 0:
                delay.append(int(tasks[0]['secs']))
                logger.info('Already training troops at castle "%s"' % city.name)
                continue

            troops = city.barracks.total_troops()

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

                        if qty > 0:
                            json = city.barracks.camp_info()
                            qty = min(qty, int(json['ret']['space']))

                            city.resource_manager.meet_requirements(Soldier.cost(cavalry.troop, qty), convert=True)
                            json = city.barracks.train_troops(cavalry.troop, qty)
                            if json['code'] == EmrossWar.SUCCESS:
                                city.countdown_manager.add_tasks(json['ret']['cdlist'])
                                logger.info('Stop processing the rest of the cavalries list at city "%s"' % city.name)
                                break
                except KeyError:
                    pass

        if delay:
            secs = (min(delay)-time.time()) / 2
            logger.info('Retry troop training in %f seconds' % secs)
            self.sleep(secs)
