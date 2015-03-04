from lib import six

from emross.api import EmrossWar
from emross.arena import CONSCRIPT_URL
from emross.arena.hero import Hero
from emross.resources import Resource
from emross.utility.task import FilterableCityTask

RUMOURS = EmrossWar.TRANSLATE['f_city_hero'].get('1', 'Rumours')
RECRUIT = EmrossWar.TRANSLATE['f_city_hero'].get('3', 'Recruit')

class HeroRecruit(FilterableCityTask):
    INTERVAL = 3600
    RUMOUR_CHECKING = False

    def process(self, recruit_heroes=[], recruit_hero_ranks=[],
                check_rumours=RUMOUR_CHECKING, *args, **kwargs):

        delays = []
        poor_cities = set()

        for city in self.cities(**kwargs):
            if city.hero_manager.remaining_hero_capacity < 1:
                self.log.debug(six.u('There is no space to recruit any further heroes at "{0}"').format(city.name))
                continue

            self.log.info(six.u('Check for heroes at the bar in "{0}"').format(city.name))
            json = self.bot.api.call(CONSCRIPT_URL, city=city.id)


            gold = int(json['ret'].get('price', 0))

            if gold and not city.resource_manager.meet_requirements({Resource.GOLD: gold}, **kwargs):
                delays.append(300)
                poor_cities.add(city)
                continue


            if 'refresh' not in json['ret']:
                self.log.info('Try buying a drink')
                json = self.bot.api.call(CONSCRIPT_URL, city=city.id, action='pub_process')

                if json['code'] == EmrossWar.REACHED_HERO_LIMIT:
                    self.log.info('Hero limit has been reached for this castle.')
                    continue

                if json['code'] == EmrossWar.INSUFFICIENT_GOLD:
                    self.log.info('Insufficient gold to buy a drink!')
                    poor_cities.add(city)
                    delays.append(300)


            delays.append(int(json['ret']['refresh']))

            if 'hero' in json['ret']:
                hero = Hero(json['ret']['hero'])

                recruit_conditions = [
                    hero.data.get('gid') in recruit_heroes,
                    hero.client.get('rank') in recruit_hero_ranks,
                ]

                if any(recruit_conditions):
                    self.log.info('Found a desired hero to recruit: {0}'.format(hero))
                    if not self.recruit_hero(city, hero):
                        delays.append(30)

        if check_rumours:
            try:
                city = [
                    city for city in self.cities(**kwargs)
                    if city not in poor_cities and
                    city.hero_manager.remaining_hero_capacity > 0
                    ][0]

                self.log.info('Checking for hero rumours')
                rumoured_heroes = self.bot.api.call(CONSCRIPT_URL,
                    city=city.id, action='rumors')['ret']['hero']

                for _hero in rumoured_heroes:
                    hero = Hero(_hero)

                    recruit_conditions = [
                        hero.data.get('gid') in recruit_heroes,
                        hero.client.get('rank') in recruit_hero_ranks,
                    ]

                    if any(recruit_conditions) and _hero['num'] == _hero['max']:
                        json = self.bot.api.call(CONSCRIPT_URL, city=city.id,
                            action='rumor_use', gid=_hero['gid'])

                        if json['code'] != EmrossWar.SUCCESS:
                            continue

                        if not self.recruit_hero(city, hero):
                            delays.append(30)
                            break
            except IndexError:
                pass

        if delays:
            self.sleep(min(delays))


    def recruit_hero(self, city, hero):
        json = self.bot.api.call(CONSCRIPT_URL, city=city.id, action='hire_process')

        if json['code'] == EmrossWar.SUCCESS:
            self.log.info(six.u('"{0}" recruited at "{1}"!').format(hero, city.name))
            city.hero_manager.expire()
            return True
        else:
            self.log.info('Could not recruit "{0}"'.format(hero))
        return False
