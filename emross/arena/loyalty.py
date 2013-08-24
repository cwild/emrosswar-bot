from emross.api import EmrossWar
from emross.arena import CONSCRIPT_GEAR_URL
from emross.arena.hero import Hero
from emross.resources import Resource
from emross.utility.task import FilterableCityTask

LOYALTY = EmrossWar.TRANSLATE['f_city_hero'].get('15', 'Loyalty:')[:-1]

class AutoLoyalty(FilterableCityTask):
    INTERVAL = 3600*6
    LOYALTY_COST = 1000
    LOYALTY_PER_DAY = 5
    MAX_LOYALTY = 100

    DAILY_HERO_REWARD_LIMIT = 1611


    def process(self, below=100, *args, **kwargs):
        """
        Try to raise our heroes loyalty to the max!
        """

        cities = self.cities(**kwargs)
        for city in cities:
            for hero in city.hero_manager.heroes.itervalues():
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
                                    city=city.id, golds=self.LOYALTY_COST)

                                if json['code'] == EmrossWar.SUCCESS:
                                    hero.data[Hero.LOYALTY] = int(json['ret']['fealty'])
                                    gold = city.resource_manager.get_amount_of(Resource.GOLD)
                                    city.resource_manager.set_amount_of(Resource.GOLD, gold-self.LOYALTY_COST)
                                elif json['code'] == self.DAILY_HERO_REWARD_LIMIT:
                                    self.log.info('Unable to raise {0} any further for {1} at the moment'.format(LOYALTY, hero))
                                    break
