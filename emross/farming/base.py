import time

from emross.api import EmrossWar
from emross.exceptions import BotException, NoTargetsAvailable, TargetException
from emross.favourites import Favourites
from emross.utility.task import FilterableCityTask

CONCURRENT_ATTACK_LIMIT = 18

class BaseFarmer(FilterableCityTask):
    INTERVAL = 60
    FAVOURITES_TYPE = Favourites.DEVIL_ARMY

    def setup(self):
        self.targets = self._find_targets()
        self._concurrent_attacks = []
        self.args = []
        self.kwargs = {}

        self.cities = self._find_cities()
        self.current_city = None

    def _find_cities(self):
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
            self.bot.favourites.get_favs(self.FAVOURITES_TYPE)
            favs = self.bot.favourites.favs[self.FAVOURITES_TYPE]
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

            # Initialise current city if it has done been accessed yet
            self.current_city = self.current_city or next(self.cities)

            self.log.debug('Begin farming loop')

            visited_targets = set()
            cycle_done = False
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
                while True:
                    if getattr(target, 'attack', 0) == self.bot.npc_attack_limit:
                        break

                    if self.current_city in visited_cities:
                        break
                    try:
                        self.process_city_with_target(self.current_city, target)
                    except TargetException as e:
                        self.log.error(e)
                        break
                    except BotException:
                        visited_cities.add(self.current_city)
                        self.current_city = next(self.cities)
                    except Exception as e:
                        self.log.exception(e)
                        break

                    if len(self.concurrent_attacks) == concurrent_attack_limit:
                        delay = max(self.concurrent_attacks) - time.time()
                        self.log.info('Maximum number of concurrent attacks, {0}, has been reached. Wait for longest current attack to return ({1} seconds)'.format(concurrent_attack_limit, delay))
                        self.sleep(delay)
                        cycle_done = True
                        break

                if cycle_done:
                    break

        except Exception as e:
            self.log.exception(e)

        try:
            self.utilities(*args, **kwargs)
        except Exception as e:
            self.log.debug('Error encountered during utilities')
            self.log.exception(e)

    def process_city_with_target(self, city, target):
        pass

    def sort_favourites(self, favs=[]):
        return favs

    def utilities(self, *args, **kwargs):
        pass
