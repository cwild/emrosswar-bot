from emross.api import EmrossWar
from emross.arena import CONSCRIPT_GEAR_URL
from emross.arena.hero import Hero
from emross.resources import Resource
from emross.utility.task import FilterableCityTask

LOYALTY = EmrossWar.TRANSLATE['f_city_hero'].get('15', 'Loyalty:')[:-1]

REVIVAL_COST = 1000

class AutoLoyalty(FilterableCityTask):
    INTERVAL = 3600*6
    LOYALTY_COST = 1000
    LOYALTY_PER_DAY = 5
    MAX_LOYALTY = 100
    FAILURE_THRESHOLD = 3
    FAILURE_THRESHOLD_PER_CITY = 1

    DAILY_HERO_REWARD_LIMIT = 1611


    def process(self, below=MAX_LOYALTY, revive=True, sleep=(1,3),  *args, **kwargs):
        """
        Try to raise our heroes loyalty to the max!
        """

        total_failures = 0
        for city in self.cities(**kwargs):
            # Track failures per city
            failures = 0

            for hero in city.hero_manager.heroes.itervalues():
                if hero.data.get(Hero.STATE) == Hero.DEAD:
                    if not revive:
                        self.log.debug('Skip {0} because it is dead'.format(hero))
                        continue

                    cost = REVIVAL_COST * hero.data.get(Hero.LEVEL)
                    if city.resource_manager.meet_requirements({Resource.GOLD: cost}, **kwargs):
                        city.hero_manager.revive_hero(hero)

                if total_failures == self.FAILURE_THRESHOLD or failures == self.FAILURE_THRESHOLD_PER_CITY:
                    # Assume that we are not yet in a position to raise loyalty on any heroes
                    continue

                loyalty = int(hero.data.get(Hero.LOYALTY, 0))
                self.log.info('{0} has {1} {2}.'.format(hero, loyalty, LOYALTY))

                if loyalty < below:
                    attempts = min([self.LOYALTY_PER_DAY, self.MAX_LOYALTY - loyalty])
                    if attempts:
                        self.log.info('Try raising {0} by {1} {2}'.format(hero, attempts, LOYALTY))
                        for attempt in range(attempts):
                            if city.resource_manager.meet_requirements({Resource.GOLD: self.LOYALTY_COST}):

                                json = self.bot.api.call(CONSCRIPT_GEAR_URL, \
                                    id=hero.data['id'], action='give', \
                                    city=city.id, golds=self.LOYALTY_COST, sleep=sleep)

                                if json['code'] == EmrossWar.SUCCESS:
                                    hero.data[Hero.LOYALTY] = int(json['ret']['fealty'])
                                    gold = city.resource_manager.get_amount_of(Resource.GOLD)
                                    city.resource_manager.set_amount_of(Resource.GOLD, gold-self.LOYALTY_COST)
                                elif json['code'] == self.DAILY_HERO_REWARD_LIMIT:
                                    total_failures += 1
                                    failures += 1
                                    self.log.info('Unable to raise {0} any further for {1} at the moment'.format(LOYALTY, hero))
                                    break
