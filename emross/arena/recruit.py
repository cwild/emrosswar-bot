from lib import six

import emross
from emross.api import EmrossWar, cache_ready
from emross.arena import CONSCRIPT_URL
from emross.arena.hero import Hero
from emross.resources import Resource
from emross.utility.task import FilterableCityTask

RUMOURS = cache_ready(lambda: globals().update(
    {'RUMOURS': EmrossWar.TRANSLATE['f_city_hero'].get('1', 'Rumours')}
))
RECRUIT = cache_ready(lambda: globals().update(
    {'RECRUIT': EmrossWar.TRANSLATE['f_city_hero'].get('3', 'Recruit')}
))

class HeroRecruit(FilterableCityTask):
    INTERVAL = 3600
    RUMOUR_CHECKING = False

    @emross.defer.inlineCallbacks
    def process(self, recruit_heroes=[], recruit_hero_ranks=[],
                check_rumours=RUMOUR_CHECKING, *args, **kwargs):

        delays = []
        poor_cities = set()

        for city in self.cities(**kwargs):
            remaining = yield city.hero_manager.remaining_hero_capacity
            if remaining < 1:
                self.log.debug(six.u('There is no space to recruit any further heroes at "{0}"').format(city.name))
                continue

            self.log.info(six.u('Check for heroes at the bar in "{0}"').format(city.name))
            json = yield self.bot.api.call(CONSCRIPT_URL, city=city.id)


            gold = int(json['ret'].get('price', 0))

            meet_requirements = yield city.resource_manager.meet_requirements({Resource.GOLD: gold}, **kwargs)
            if gold and not meet_requirements:
                delays.append(300)
                poor_cities.add(city)
                continue


            if 'refresh' not in json['ret']:
                self.log.debug(gettext('Try buying a drink'))
                json = yield self.bot.api.call(CONSCRIPT_URL, city=city.id, action='pub_process')

                if json['code'] == EmrossWar.REACHED_HERO_LIMIT:
                    self.log.debug(gettext('Hero limit has been reached for this castle.'))
                    continue

                if json['code'] == EmrossWar.INSUFFICIENT_GOLD:
                    self.log.info(gettext('Insufficient gold to buy a drink!'))
                    poor_cities.add(city)
                    delays.append(300)


            delays.append(int(json['ret']['refresh']))

            if 'hero' in json['ret']:
                hero = Hero(json['ret']['hero'])

                recruit_conditions = (
                    hero.data.get('gid') in recruit_heroes or
                    hero.client.get('rank') in recruit_hero_ranks
                )

                if recruit_conditions:
                    self.log.info(gettext('Found a desired hero to recruit: {0}').format(hero))
                    recruited = yield self.recruit_hero(city, hero)
                    if not recruited:
                        delays.append(30)

        if check_rumours:
            city = None
            for _city in self.cities(**kwargs):
                if _city not in poor_cities:
                    capacity = yield _city.hero_manager.remaining_hero_capacity
                    if capacity > 0:
                        city = _city
                        break

            self.log.info(gettext('Checking for hero rumours'))
            rumoured_heroes = yield self.bot.api.call(CONSCRIPT_URL,
                city=city.id, action='rumors')['ret']['hero']

            for _hero in rumoured_heroes:
                hero = Hero(_hero)

                recruit_conditions = (
                    hero.data.get('gid') in recruit_heroes or
                    hero.client.get('rank') in recruit_hero_ranks
                )

                if recruit_conditions and _hero['num'] == _hero['max']:
                    json = yield self.bot.api.call(CONSCRIPT_URL, city=city.id,
                        action='rumor_use', gid=_hero['gid'])

                    if json['code'] != EmrossWar.SUCCESS:
                        continue

                    recruited = yield self.recruit_hero(city, hero)
                    if not recruited:
                        delays.append(30)
                        break

        if delays:
            self.sleep(min(delays))


    @emross.defer.inlineCallbacks
    def recruit_hero(self, city, hero):
        json = yield self.bot.api.call(CONSCRIPT_URL, city=city.id, action='hire_process')

        if json['code'] == EmrossWar.SUCCESS:
            self.log.info(six.u(gettext('"{0}" recruited at "{1}"!')).format(hero, city.name))
            city.hero_manager.expire()
            emross.defer.returnValue(True)
        else:
            self.log.info(gettext('Could not recruit "{0}"').format(hero))
        emross.defer.returnValue(False)
