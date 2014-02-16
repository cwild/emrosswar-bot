from emross.api import EmrossWarApi
from emross.arena.hero import Hero
from emross.downtown.city import City
from emross.military.camp import Soldier
from emross.research.studious import Study
from emross.utility.helper import EmrossWarBot

from lib.cacheable import CacheableData
CacheableData.LOCKED = True


bot = EmrossWarBot(
    EmrossWarApi(None, 'localhost')
)

# setup our cities
bot._cities = [
    City(bot, 1, 'city.A', x=10, y=20),
    City(bot, 2, 'city.B', x=11, y=21),
    City(bot, 3, 'city.C', x=12, y=22),
    City(bot, 4, 'city.D', x=13, y=23),
]

study = bot.builder.task(Study)

for c in bot._cities:
    c._data = [5, 194, 19061, 582188, 212508, 582188, 29219, 582188, 43928, \
            582188, 2348, 15541, 0, 0, 3, 30, 21, 30, 30, 21, 4, 30, 20, [], 0]

    # Max techs, (tech, level, unlocked)
    study._cities[c] = [(i, 20, 1) for i in range(24)]


# Maxed-out hall
bot.alliance._info = [5, 1200300400, '?', 1000000, 0,
    [(0,5,0) for _ in range(20)]
]

# troop data
bot.cities[0].barracks._soldier_data = {
    Soldier.OVERLORD: {'a': 300, 'e': 280, 'd': 180, 'f': 12, 'h': 450, 's': 350},
    Soldier.KAHKLEH: {'a': 500, 'e': 250, 'd': 240, 'f': 54, 'h': 800, 's': 450},
}
