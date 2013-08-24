from emross.api import EmrossWar
from emross.arena import CONSCRIPT_URL
from emross.arena.hero import Hero
from emross.resources import Resource
from emross.structures.buildings import Building
from emross.structures.construction import Construct
from emross.utility.task import FilterableCityTask

RUMOURS = EmrossWar.TRANSLATE['f_city_hero'].get('1', 'Rumours')
RECRUIT = EmrossWar.TRANSLATE['f_city_hero'].get('3', 'Recruit')

class HeroRecruit(FilterableCityTask):
    INTERVAL = 3600

    def process(self, recruit_heroes=[], *args, **kwargs):

        cities = self.cities(**kwargs)
        st = self.bot.builder.task(Construct)
        delays = []
        for city in cities:
            if st.structure_level(city, Building.ARENA) < 1:
                self.log.info('There is no arena at {1}'.format(city.name))
                continue

            self.log.info('Check for heroes at the bar in "{0}"'.format(city.name))
            json = self.bot.api.call(CONSCRIPT_URL, city=city.id)

            gold = None
            if 'price' in json['ret']:
                gold = int(json['ret']['price'])

            if 'refresh' in json['ret']:
                self.log.info('We have to wait before we can do this. Timer: {0}'.format(json['ret']['refresh']))
                delays.append(int(json['ret']['refresh']))
            elif gold:
                if not city.resource_manager.meet_requirements({Resource.GOLD: gold}, **kwargs):
                    delays.append(300)
                    continue

                self.log.info('Try buying a drink')
                json = self.bot.api.call(CONSCRIPT_URL, city=city.id, action='pub_process')

                if json['code'] == EmrossWar.REACHED_HERO_LIMIT:
                    self.log.info('Hero limit has been reached for this castle.')
                    continue

                if json['code'] == EmrossWar.INSUFFICIENT_GOLD:
                    self.log.info('Insufficient gold to buy a drink!')
                    delays.append(300)
                else:
                    delays.append(int(json['ret']['refresh']))


                if 'hero' in json['ret'] and json['ret']['hero']['gid'] in recruit_heroes:
                    hero = Hero(json['ret']['hero']['gid'])
                    self.log.info('Found a hero we are looking for: {0}'.format(hero.client.get('name')))
                    json = self.bot.api.call(CONSCRIPT_URL, city=city.id, action='hire_process')

                    if json['code'] == EmrossWar.SUCCESS:
                        self.log.info('{0} recruited!'.format(hero))
                    else:
                        self.log.info('Could not recruit {0}'.format(hero))

        if delays:
            self.sleep(min(delays))
