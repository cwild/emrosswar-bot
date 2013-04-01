import time
import logging
logger = logging.getLogger(__name__)

from emross.api import EmrossWar
from emross.exceptions import WorldException, OutOfSpies
from emross.military.barracks import Barracks
from emross.military.camp import Soldier

class World:
    MAP_URL = 'game/api_world_map.php'

    def __init__(self, bot):
        self.bot = bot
        self._map_size = None

    def scout(self, city, x, y):
        """
        Scout the co-ord
        """

        """ These x,y params seem backwards, d'oh!"""
        params = {
            'city': city.id,
            'action': 'do_war',
            'attack_type': EmrossWar.ATTACK_TYPE_SCOUT,
            'tai_num': 1,
            'area': x,
            'area_x': y
        }
        json = city.barracks.confirm_and_do(params)
        return json['code'] == EmrossWar.SUCCESS


    def get_city_with_spies(self):
        """Choose a city with spies"""
        choice = None
        for city in self.bot.cities:
            city.barracks.get_soldiers()
            try:
                if city.barracks.soldiers[Soldier.SPY-1][1]:
                    if not choice or city.barracks.soldiers[Soldier.SPY-1][1] > choice.barracks.soldiers[Soldier.SPY-1][1]:
                        choice = city
            except IndexError:
                pass

        if choice:
            logger.info('Sending spies from %s' % choice.name)
            return choice

        logger.info('Unable to locate any available spies, sleeping for 5 mins.')
        time.sleep(300)


    def search(self, targets = []):
        if not targets:
            logger.info('No targets to scout')
            return

        city = self.get_city_with_spies()
        if not city:
            logger.info('No cities found with spies.')
            return

        try:
            x, y, nx, ny = self.bot.session.map_coords
            page = self.get_page(x, y)
        except AttributeError:
            x, y, nx, ny = 1, 1, 1, 1
            page = self.get_page(x, y)
            nx = page['xleft']
            ny = page['yup']
        finally:
            logger.debug('Map co-ordinates: %s' % str((x, y, nx, ny)))

        self.favs = self.bot.fav[EmrossWar.DEVIL_ARMY]

        spies = 0

        while y < ny:

            while x < nx:
                self.bot.session.map_coords = (x, y, nx, ny)

                try:
                    for item in page['map']:
                        if item[2] in targets:
                            if not spies:
                                for tries in xrange(2):
                                    city.barracks.get_soldiers()
                                    spies = city.barracks.soldiers[Soldier.SPY-1][1]
                                    logger.info('Found %d spies in the city %s' % (spies, city.name))
                                    if not spies:
                                        if tries == 0:
                                            logger.info('Check the war room. Try to trigger spy count to update')
                                            city.barracks.war_room()
                                        else:
                                            raise OutOfSpies, 'No spies available at the moment'
                                    else:
                                         break


                            favs = [f for f in self.favs if f.x == item[1] and f.y == item[0]]
                            if favs:
                                logger.info('Already a fav, skipping')
                                continue

                            logger.info('Scouting [%d, %d]' % (item[0], item[1]))
                            self.scout(city, item[0], item[1])
                            spies -= 1



                    if page['xright'] > x:
                        x = page['xright']
                        page = self.get_page(x, y)
                    else:
                        break

                except WorldException:
                    logger.info('Sleeping for 5 mins')
                    time.sleep(600)


            if page['ydown'] > y:
                y = page['ydown']
                page = self.get_page(x, y)
            else:
                try:
                    del self.bot.session.map_coords
                except AttributeError:
                    pass

                logger.info('Finished scouting map')
                break

            x = 0

    def get_page(self, x, y):
        logger.info('Get page x=%d y=%d' % (x,y))
        json = self.bot.api.call(self.MAP_URL, x=x, y=y)

        return json['ret']

    def map_size(self, x = 1, y = 1):
        if self._map_size:
            return self._map_size

        data = self.get_page(x, y)
        nx = data['xleft'] + data['xright'] - x-1
        ny = data['yup'] + data['ydown'] - y-1
        self._map_size = (nx, ny)
        return self._map_size


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    from bot import bot

    x, y = 1, 1
    logger.info('The boundaries of this world map are (%d, %d), (%d, %d).' % ((x, y)+bot.world.map_size(x, y)))
