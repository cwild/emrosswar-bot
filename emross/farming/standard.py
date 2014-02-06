import time

from emross.api import EmrossWar
from emross.arena.hero import Hero
from emross.exceptions import (EmrossWarApiException,
    InsufficientSoldiers,
    NoHeroesAvailable,
    NoTargetsAvailable,
    NoTargetsFound)
from emross.farming.base import BaseFarmer
from emross.favourites import Favourites
from emross.military.barracks import Barracks


class BasicFarmer(BaseFarmer):
    INTERVAL = 300

    def process_city_with_target(self, city, target):
        soldier_threshold = self.kwargs.get('soldier_threshold')

        try:
            threshold = [thresholds for rating, thresholds in soldier_threshold
                            if rating == target.rating][0]
        except IndexError:
            return

        army = city.create_army(threshold)
        hero = city.choose_hero(sum(army.values()), **self.kwargs)

        self.log.info('Sending attack: [{0}/{1}] {2} from "{3}"'.format(\
            target.y, target.x, hero, city.name))

        # send troops to attack
        params = {
            'action': 'do_war',
            'attack_type': Barracks.ATTACK,
            'gen': hero.data['gid'],
            'area': target.y,
            'area_x': target.x
        }
        params.update(army)

        json = city.barracks.confirm_and_do(params, sleep_confirm=(5,8), sleep_do=(1,3))

        roundtrip = params.get('travel_sec', 0) * 2
        self.concurrent_attacks.append(time.time() + roundtrip)

        if json['code'] == EmrossWar.SUCCESS:
            target.attack += 1
            hero.data[Hero.STATE] = Hero.WAR


    def sort_favourites(self, favs=[]):
        """
        Sort based on the ratings, as soldier_threshold always did.
        """
        soldier_threshold = self.kwargs.get('soldier_threshold', [])
        ratings = [rating for rating, thresholds in soldier_threshold]
        fav_by_rating = {}

        for fav in favs:
            if fav.rating in ratings:
                fav_by_rating.setdefault(fav.rating, []).append(fav)


        favs[:] = []
        for rating in ratings:
            favs.extend(fav_by_rating.get(rating, []))

        return favs

    def utilities(self, *args, **kwargs):
        self.bot.scout_map(targets=kwargs.get('scout_devil_army_types', []), **kwargs)
        self.bot.clean_war_reports()

        if not self.bot.pvp and kwargs.get('allow_inventory_clearout', True):
            self.bot.clearout_inventory()

        cities = super(BasicFarmer, self).cities(**self.kwargs)
        for city in cities:
            city.replenish_food()

        self.log.info(self.bot.total_wealth())
