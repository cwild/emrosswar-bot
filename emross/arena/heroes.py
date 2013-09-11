from emross.api import EmrossWar
from emross.arena.hero import Hero
from emross.utility.base import EmrossBaseObject
from lib.cacheable import CacheableData

from emross.arena import CONSCRIPT_URL, CONSCRIPT_GEAR_URL

class HeroManager(EmrossBaseObject, CacheableData):

    def __init__(self, bot, city):
        super(HeroManager, self).__init__(bot)
        self.city = city
        self._heroes = {}

    @property
    def heroes(self):
        _ = self.data
        return self._heroes

    def update(self):
        self.log.info('Update heroes at city "{0}"'.format(self.city.name))

        json = self.bot.api.call(CONSCRIPT_URL, city=self.city.id, action='gen_list')

        if json['code'] == EmrossWar.SUCCESS:
            heroes = set()
            for hero in json['ret']['hero']:
                hero_id = hero['id']
                heroes.add(hero_id)
                try:
                    self._heroes[hero_id].update(hero)
                except KeyError:
                    self._heroes[hero_id] = Hero(hero)

            # Remove heroes which are not present
            old_heroes = set(self._heroes.keys())-heroes
            for hero in old_heroes:
                del self._heroes[hero]

            return json

    def highest_stat_hero(self, stat=Hero.COMMAND):
        try:
            hero = self.ordered_by_stats(stats=(stat,))[0]
            self.log.debug(hero)
            attr_name = Hero.ATTRIBUTE_NAMES.get(stat, 'UNKNOWN')
            self.log.info('{0} with {1} {2}'.format(hero, hero.data.get(stat), attr_name))
            return hero
        except IndexError:
            pass

    def ordered_by_stats(self, stats=[Hero.LEVEL, Hero.EXPERIENCE], exclude=[]):
        exclude = set(exclude)
        heroes = [hero for hero in self.heroes.values() if hero.stat('gid') not in exclude]
        heroes.sort(key = lambda hero: [hero.data.get(stat) for stat in stats], reverse=True)
        return heroes

    def ordered_by_scored_stats(self, scoring=[(Hero.COMMAND, 1)], heroes=None, exclude=[]):
        result = []
        exclude = set(exclude)
        heroes = self.heroes if heroes is None else heroes

        for hero_id, hero in heroes.iteritems():
            if hero_id in exclude:
                self.log.debug('Exclude hero {0}'.format(hero_id))
                continue

            score = 0
            for stat, weight in scoring:
                score += hero.data.get(stat, 0) * weight
            result.append((hero, score))

        result.sort(key = lambda hero: hero[1], reverse=True)
        self.log.debug(result)

        return result

    def revive_hero(self, hero):
        """
        Given a hero, try reviving it from the dead!
        """
        self.log.debug('Try to revive {0} at "{1}"'.format(hero, self.city.name))
        json = self.bot.api.call(CONSCRIPT_GEAR_URL, id=hero.data['id'], action='relive', city=self.city.id)

        if json['code'] == EmrossWar.SUCCESS:
            self.log.info('Revived {0} at "{1}"'.format(hero, self.city.name))
            hero.data[Hero.STATE] = Hero.AVAILABLE

        return json
