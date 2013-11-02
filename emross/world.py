import time

from emross.api import EmrossWar
from emross.exceptions import WorldException, OutOfSpies
from emross.favourites import Favourites
from emross.military.camp import Soldier
from emross.utility.task import Task

class World(Task):
    MAP_URL = 'game/api_world_map.php'
    PLAYER_NODE = -1

    def __init__(self, bot, *args, **kwargs):
        super(World, self).__init__(bot, *args, **kwargs)
        self._map_size = None

    def scout(self, city, x, y):
        """
        Scout the co-ord
        """

        """ These x,y params seem backwards, d'oh!"""
        params = {
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
            self.log.info('Sending spies from {0}'.format(choice.name))
            return choice

        self.log.info('Unable to locate any available spies, sleeping for 5 mins.')
        time.sleep(300)


    def search(self, targets=[]):
        if not targets:
            self.log.info('No targets to scout')
            return

        city = self.get_city_with_spies()
        if not city:
            self.log.info('No cities found with spies.')
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
            self.log.debug('Map co-ordinates: {0}'.format((x, y, nx, ny)))

        self.favs = self.bot.favourites.favs[Favourites.DEVIL_ARMY]

        spies = 0

        while y < ny:

            while x < nx:
                self.bot.session.map_coords = (x, y, nx, ny)

                try:
                    for item in page['map']:
                        if item[2] in targets:
                            if spies < 1:
                                for tries in xrange(2):
                                    city.barracks.get_soldiers()
                                    spies = city.barracks.soldiers[Soldier.SPY-1][1]
                                    self.log.info('Found {0} spies in the city {}'.format(spies, city.name))
                                    if spies < 1:
                                        if tries == 0:
                                            self.log.info('Check the war room. Try to trigger spy count to update')
                                            city.barracks.war_room()
                                        else:
                                            raise OutOfSpies('No spies available at the moment')
                                    else:
                                         break


                            favs = [f for f in self.favs if f.x == item[1] and f.y == item[0]]
                            if favs:
                                self.log.info('Already a fav, skipping')
                                continue

                            self.log.info('Scouting [{0}, {1}]'.format(item[0], item[1]))
                            if not self.scout(city, item[0], item[1]):
                                raise OutOfSpies('Not enough spies')

                            spies -= 1



                    if page['xright'] > x:
                        x = page['xright']
                        page = self.get_page(x, y)
                    else:
                        break

                except WorldException:
                    self.log.info('Sleeping for 5 mins')
                    time.sleep(300)


            if page['ydown'] > y:
                y = page['ydown']
                page = self.get_page(x, y)
            else:
                try:
                    del self.bot.session.map_coords
                except AttributeError:
                    pass

                self.log.info('Finished scouting map')
                break

            x = 0

    def get_page(self, x, y):
        self.log.info('Get page x={0} y={1}'.format(x,y))
        json = self.bot.api.call(self.MAP_URL, x=x, y=y)

        return json['ret']

    def get_point(self, x, y):
        nodes = self.get_page(x, y)
        search_node = map(int, [x,y])

        for node in nodes['map']:
            if node[:2] == search_node:
                return node

    def map_size(self, x=1, y=1):
        if self._map_size:
            return self._map_size

        data = self.get_page(x, y)
        nx = data['xleft'] + data['xright'] - x-1
        ny = data['yup'] + data['ydown'] - y-1
        self._map_size = (nx, ny)
        return self._map_size


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)

    from bot import bot

    x, y = 1, 1
    logging.info('The boundaries of this world map are (%d, %d), (%d, %d).' % ((x, y)+bot.world.map_size(x, y)))
