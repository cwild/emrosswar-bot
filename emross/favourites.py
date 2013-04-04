import logging
import math

from emross.api import EmrossWar
from emross.mobs import NPC

logger = logging.getLogger(__name__)

class Favourites(object):
    FAV_URL = 'game/api_fav.php'
    LORD = 1
    DEVIL_ARMY = 2
    COLONY = 3

    TYPES = {
        DEVIL_ARMY: NPC
    }

    def __init__(self, bot):
        self.bot = bot
        self.favs = {}

    def add(self, wid, cat):
        return self.bot.api.call(self.FAV_URL, act='addreport', wid=wid, cat=cat)

    def clear_favs(self, cat=DEVIL_ARMY):
        for f in self.favs[cat]:
            logger.info('Deleting fav %d' % f.id)
            self.bot.api.call(self.FAV_URL, act='delfavnpc', fid=f.id)

    def get_favs(self, cat=DEVIL_ARMY):
        json = self.bot.api.call(self.FAV_URL, act='getfavnpc', cat=cat)
        favs = json['ret']['favs']

        self.favs[cat] = []
        for data in favs:
            fav = self.TYPES[cat](data)
            self.favs[cat].append(fav)

    def sort_favs(self, city, cat=DEVIL_ARMY):
        """
        Sort favs based on proximity from city (ascending distance)
        """
        nx, ny = city.y, city.x # Backwards..?
        max = self.bot.world.map_size()
        self.favs[cat].sort(key=lambda fav: math.sqrt( min(abs(fav.x-nx), max[0]-abs(fav.x-nx))**2  + min( abs(fav.y-ny), max[1]-abs(fav.y-ny) )**2) )


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    from bot import bot

    fm = Favourites(bot)
    fm.get_favs()

