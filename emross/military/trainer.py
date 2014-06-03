import time

from emross.api import EmrossWar
from emross.arena.hero import Hero
from emross.military.camp import Soldier
from emross.structures.buildings import Building
from emross.structures.construction import Construct
from emross.utility.task import FilterableCityTask, TaskType


class Cavalry:
    USE_HERO = False
    WAIT_FOR_HERO = True

    def __init__(self, troop, quantity, minimum=0,
                use_hero=USE_HERO, wait_for_hero=WAIT_FOR_HERO,
                *args, **kwargs):
        self.troop = troop
        self.quantity = quantity
        self.minimum = minimum
        self.use_hero = use_hero
        self.wait_for_hero = wait_for_hero


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
                self.log.debug(u'There is no Barracks at {0}'.format(city))
                continue

            delay = None
            tasks = city.countdown_manager.get_tasks(task_type=TaskType.TRAIN)
            if len(tasks) > 0:
                delays.append(int(tasks[0]['secs'])-time.time())
                self.log.debug(u'Already training troops at {0}'.format(city))
                continue

            troops = city.barracks.total_troops()
            camp_space = int(city.barracks.data.get('space', 0))

            for cavalry in cavalries:
                try:
                    if not city.barracks.can_train(cavalry.troop):
                        self.log.debug(u'Cannot train troop type {0} at {1}'.format(cavalry.troop, city))
                        continue

                    if cavalry.quantity > troops[cavalry.troop]:
                        desired = cavalry.quantity - troops[cavalry.troop]
                        self.log.debug(u'Shortfall of {0} troops of type {1} at {2}'.format(desired, cavalry.troop, city))

                        qty = 0
                        maximum = min(camp_space, desired)
                        while qty < maximum and city.resource_manager.meet_requirements(Soldier.cost(cavalry.troop, qty+1), convert=False):
                            qty += 1

                        if 0 < qty >= cavalry.minimum:
                            city.resource_manager.meet_requirements(Soldier.cost(cavalry.troop, qty), convert=True)

                            hero_id = 0
                            if cavalry.use_hero:
                                hero = city.hero_manager.highest_stat_hero(Hero.ATTACK)
                                if hero and hero.stat(Hero.VIGOR) and hero.stat(Hero.STATE) == Hero.AVAILABLE:
                                    hero_id = hero.data.get('gid', 0)
                                    self.log.info(u'Chosen to train troops with "{0}" at {1}'.format(hero, city))
                                elif cavalry.wait_for_hero:
                                    continue

                            json = city.barracks.train_troops(cavalry.troop, qty, hero_id)

                            if json['code'] == EmrossWar.SUCCESS:
                                delay = int(json['ret']['cdlist'][0]['secs'])
                                city.countdown_manager.add_tasks(json['ret']['cdlist'])
                                self.log.debug(u'Stop processing the rest of the cavalries list at {0}'.format(city))
                                break
                except KeyError:
                    pass

            if delay:
                delays.append(delay)

        if delays:
            secs = max(self.MINIMUM_CHECK_PERIOD, min(delays) / 2)
            self.log.info('Retry troop training in {0} seconds'.format(secs))
            self.sleep(secs)
