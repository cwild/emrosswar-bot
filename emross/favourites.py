import collections
import math

# Needs to be defined ahead of NPC import
FAVOURITES_URL = 'game/api_fav.php'

from emross.api import EmrossWar
from emross.mobs.npc import NPC
from emross.utility.controllable import Controllable

class GenericFavourite(object):
    def __init__(self, data, bot):
        self.data = data
        self.id = data[0]
        self.x = data[1]
        self.y = data[2]


class Favourites(Controllable):
    COMMAND = 'favs'
    LORD = None
    DEVIL_ARMY = 2
    COLONY = 1

    TYPES = {
        DEVIL_ARMY: NPC
    }

    def __init__(self, bot):
        super(Favourites, self).__init__(bot)
        self.favs = collections.defaultdict(list)

    @Controllable.restricted
    def action_clear(self, event, *args, **kwargs):
        self.clear_favs(*args, **kwargs)

    def action_status(self, event, *args, **kwargs):
        """
        Find out the current state of the favourites list
        """
        self.get_favs()

        favs = self.favs[self.DEVIL_ARMY]
        self.chat.send_message('{num}*{monster}: {remain} remaining loots.'.format(\
            num=len(favs),
            monster=EmrossWar.LANG.get('MONSTER', 'NPCs'),
            remain=sum([self.bot.npc_attack_limit - x.attack for x in favs])
        ))

    def add(self, wid, cat):
        return self.bot.api.call(FAVOURITES_URL, act='addreport', wid=wid, cat=cat)

    def clear_favs(self, cat=DEVIL_ARMY, *args, **kwargs):
        cat = int(cat)
        for f in self.favs[cat]:
            self.log.info('Deleting fav {0}'.format(f.id))
            self.bot.api.call(FAVOURITES_URL, act='delfavnpc', fid=f.id)

    def get_favs(self, cat=DEVIL_ARMY):
        json = self.bot.api.call(FAVOURITES_URL, act='getfavnpc', cat=cat)
        favs = json['ret']['favs']

        self.favs[cat][:] = []
        for data in favs:
            fav = self.TYPES.get(cat, GenericFavourite)(data, self.bot)
            self.favs[cat].append(fav)

    def sort_favs(self, city, cat=DEVIL_ARMY):
        """
        Sort favs based on proximity from city (ascending distance)
        """
        nx, ny = city.y, city.x # Backwards..?
        max = self.bot.world.map_size()
        self.favs[cat].sort(key=lambda fav: math.sqrt( min(abs(fav.x-nx), max[0]-abs(fav.x-nx))**2  + min( abs(fav.y-ny), max[1]-abs(fav.y-ny) )**2) )


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    from bot import bot

    fm = Favourites(bot)
    fm.get_favs()
