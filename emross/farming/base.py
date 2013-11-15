import time

from emross.api import EmrossWar
from emross.exceptions import (EmrossWarApiException,
    BotException)
from emross.favourites import Favourites
from emross.utility.task import FilterableCityTask

CONCURRENT_ATTACK_LIMIT = 18

class BaseFarmer(FilterableCityTask):
    INTERVAL = 60

    def setup(self):
        self.targets = self._find_targets()
        self._concurrent_attacks = []
        self.args = []
        self.kwargs = {}

    @property
    def cities(self):
        while True:
            cities = super(BaseFarmer, self).cities(**self.kwargs)
            for city in cities:
                yield city

    @property
    def concurrent_attacks(self):
        self._concurrent_attacks[:] = [attack for attack in \
                    self._concurrent_attacks if time.time() < attack]

        return self._concurrent_attacks

    def _find_targets(self):
        while True:
            self.bot.favourites.get_favs(Favourites.DEVIL_ARMY)
            favs = self.bot.favourites.favs[Favourites.DEVIL_ARMY]
            favs[:] = self.sort_favourites(favs)

            if len(favs) == 0:
                yield NoTargetsAvailable('No favourites are available to attack')
                continue

            for target in favs:
                yield target

    def process(self, concurrent_attack_limit=CONCURRENT_ATTACK_LIMIT,
            *args, **kwargs):
        """
        Implement the most basic functions that a farmer will perform
        """
        try:
            # Allow other methods to access these
            self.args, self.kwargs = args, kwargs

            self.log.debug('Begin farming loop')

            visited_targets = set()
            for target in self.targets:

                if isinstance(target, Exception):
                    raise target

                if target.id in visited_targets:
                    break
                visited_targets.add(target.id)

                """
                Cities should flag when they have no available heroes so we only
                check them once per target.
                """
                visited_cities = set()
                target_done = False

                for i in range(self.bot.npc_attack_limit - target.attack):

                    for city in self.cities:
                        if target.attack == self.bot.npc_attack_limit:
                            target_done = True
                            break

                        if city in visited_cities:
                            break
                        try:
                            self.process_city_with_target(city, target)
                        except BotException:
                            visited_cities.add(city)

                        if len(self.concurrent_attacks) == concurrent_attack_limit:
                            delay = max(self.concurrent_attacks) - time.time()
                            self.log.info('Maximum number of concurrent attacks, {0}, has been reached. Wait for longest current attack to return ({1} seconds)'.format(concurrent_attack_limit, delay))
                            self.sleep(delay)
                            return

                    # Finished with this target? Move onto the next one!
                    if target_done:
                        break

            self.utilities(*args, **kwargs)

        except Exception as e:
            self.log.exception(e)

    def process_city_with_target(self, city, target):
        pass

    def sort_favourites(self, favs=[]):
        return favs

    def utilities(self, *args, **kwargs):
        pass