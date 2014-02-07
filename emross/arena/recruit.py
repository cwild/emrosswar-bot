from __future__ import division

import math

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

    def process(self, recruit_heroes=[], recruit_hero_ranks=[], *args, **kwargs):

        st = self.bot.builder.task(Construct)
        delays = []

        for city in self.cities(**kwargs):
            arena = st.structure_level(city, Building.ARENA)

            if arena < 1:
                self.log.debug('There is no arena at "{0}"'.format(city.name))
                continue

            capacity = math.ceil(arena / 2)
            if capacity <= len(city.hero_manager.heroes):
                self.log.debug('There is no space to recruit any further heroes at "{0}"'.format(city.name))
                continue

            self.log.info('Check for heroes at the bar in "{0}"'.format(city.name))
            json = self.bot.api.call(CONSCRIPT_URL, city=city.id)


            gold = int(json['ret'].get('price', 0))

            if gold and not city.resource_manager.meet_requirements({Resource.GOLD: gold}, **kwargs):
                delays.append(300)
                continue


            if 'refresh' not in json['ret']:
                self.log.info('Try buying a drink')
                json = self.bot.api.call(CONSCRIPT_URL, city=city.id, action='pub_process')

                if json['code'] == EmrossWar.REACHED_HERO_LIMIT:
                    self.log.info('Hero limit has been reached for this castle.')
                    continue

                if json['code'] == EmrossWar.INSUFFICIENT_GOLD:
                    self.log.info('Insufficient gold to buy a drink!')
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

                    json = self.bot.api.call(CONSCRIPT_URL, city=city.id, action='hire_process')

                    if json['code'] == EmrossWar.SUCCESS:
                        self.log.info('"{0}" recruited at "{1}"!'.format(hero, city.name))
                    else:
                        self.log.info('Could not recruit "{0}"'.format(hero))

        if delays:
            self.sleep(min(delays))
