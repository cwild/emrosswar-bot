import logging

from emross.api import EmrossWar
from emross.arena.hero import Hero

logger = logging.getLogger(__name__)

class HeroManager(object):
    URL = 'game/gen_conscribe_api.php'

    def __init__(self, bot, city):
        self.bot = bot
        self.city = city
        self._heroes = None

    @property
    def heroes(self):
        if self._heroes is None:
            self._heroes = {}
            self.update()
        return self._heroes

    def update(self):
        logger.info('Update heroes at city "{0}"'.format(self.city.name))

        json = self.bot.api.call(self.URL, city=self.city.id, action='gen_list')

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
                del self.heroes[hero]

    def highest_stat_hero(self, stat=Hero.COMMAND):
        try:
            hero = self.ordered_by_stats(stats=(stat,))[0]
            logger.debug(hero)
            attr_name = Hero.ATTRIBUTE_NAMES.get(stat, 'UNKNOWN')
            logger.info('{0} with {1} {2}'.format(hero, hero.data.get(stat), attr_name))
            return hero
        except IndexError:
            pass

    def ordered_by_stats(self, stats=[Hero.LEVEL, Hero.EXPERIENCE], reverse=True):
        heroes = self.heroes.values()
        heroes.sort(key = lambda hero: [hero.data.get(stat) for stat in stats], reverse=reverse)
        return heroes

    def ordered_by_scored_stats(self, scoring=[(Hero.COMMAND, 1)]):
        result = []

        for hero_id, hero in self.heroes.iteritems():
            score = 0
            for stat, weight in scoring:
                score += hero.data.get(stat, 0) * weight
            result.append((hero, score))

        result.sort(key = lambda hero: hero[1], reverse=True)
        logger.debug(result)

        return result
