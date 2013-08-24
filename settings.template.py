from emross.military.camp import Soldier
from emross.mobs import DevilArmy

user_agent = 'Mozilla/5.0 (iPhone; U; CPU iPhone OS 4_3_2 like Mac OS X; en-us) AppleWebKit/533.17.9 (KHTML, like Gecko) Mobile/8H7'

game_server = 'YOURSERVER.emrosswar.com'
api_key = ''
pushid = ''

from emross.utility.player import Player
multi_bot = []
multi_bot.append(Player(server='s1.emrosswar.com',key='key1...'))
multi_bot.append(Player(server='s2.emrosswar.com',key='key2...',pushid='abc'))
multi_bot.append(Player(server='s3.emrosswar.com',key='key3...',user_agent='my custom agent'))


"""Id = 12553, name = crow tree
--Id = 21111, name = localhost
Id = 21261, name = 127001
Id = 21469, name = Meadery
Id = 21824, name = Sparta
Id = 22008, name = Reboot"""
ignore_cities = [22008]

"""
Fill the castle food only to the specified minimum level.
If this is unspecified, the storage will be filled to max capacity.
"""
#minimum_food = 100000


TOO_OFTEN_WARNING = '''You visit too often!'''
concurrent_attack_limit = 18

exclude_heroes = []


"""
What types of Devil Army should we scout on the world map?
"""
scout_devil_army_types = [DevilArmy.FIVE_STAR, DevilArmy.SIX_STAR]

"""
It will start attacking from the first in the list, moving through the list
if there are not enough troops in the current city to build an army
"""
soldier_threshold = [
	(DevilArmy.SIX_STAR, {
		Soldier.OVERLORD: 600,
		Soldier.BERSERKER: 800
	}),
	(DevilArmy.FIVE_STAR, {
		Soldier.OVERLORD: 400,
		Soldier.BERSERKER: 600
	})
]


"""                                                                                                                                                  
Maximum number of troops which we will consider attacking

eg.
Horror 100
Nightmare 200
Inferno 9500
"""
enemy_troops = (('Horror', 100), ('Nightmare', 200), ('Inferno', 9500))


prefer_closer = True

"""
You can set the times at which you would like to farm here.

The default is all day. You can set multiple ranges here though. eg.
[(6, 9), (15, 18), (22, 23)]
"""
farming_hours = [(-1, 25)]


plugin_api = {
    'auth': 'username:password',
    'url': 'http://emross.cryformercy.com/client/plugins/api/'
}


from emross.research.studious import Study
from emross.research.tech import Tech
from emross.structures.buildings import Building
from emross.structures.construction import Construct

from emross.scenario.scene import Scenario
from emross.scenario.walker import ScenarioWalker

from emross.item import inventory
from emross.trade.auto import AutoTrade


trade_options = (AutoTrade, (AutoTrade.SELLER, [inventory.ALLIANCE_TOKEN]),
            {'price':5000000, 'vary':50000, 'limit':3, 'city_index':-1}
        )

#trade_options = (AutoTrade, (AutoTrade.BUYER, 900), {'team':True})

from emross.military.trainer import Cavalry, Trainer

from emross import pvp

from emross.alliance import AllyTech as AT, Donator
from emross.research.enhance import AutoEnhance

build_path = (
    (
        (Donator, ([AT.VETERAN, AT.VALOR, AT.TENACITY, AT.INCENTIVE, AT.TOUGHNESS,
                    AT.INSPIRATION, AT.BATTLECRY, AT.MILICADEMY, AT.BLOODFLAG, AT.LOGISTICS],),
                    {'pvp_donate':False, 'force_hall_donation':False}
        ),
        (pvp.Durability, (100,), {'stop_below': 4}),
        (Trainer, ([Cavalry(Soldier.SPY, 50)],) ),
        (Trainer, (
            [
                Cavalry(Soldier.LONUFAL, 3000),
                Cavalry(Soldier.MASTER, 3000),
                Cavalry(Soldier.KAHKLEH, 5000)
            ],),
            {'city_names': ['my_main_city', 'my_other_city']}
        )
    ),
    (
        (AutoEnhance, ([(95, 10000000), (75, 6000000), (40, 2000000), (5, 20000)],), {
            'minimum_enhance': 2
        }),
        trade_options,
    ),
    (
        (ScenarioWalker, (Scenario.GLOOMY_CANYON, [
            {
                'hero': 4,
                'troops': [(Soldier.LONUFAL, 1400), (Soldier.KAHKLEH, 1644)],
                'path': [1, 5, 4, 11, 13]
            },
            {
                'hero': 222,
                'troops': [(Soldier.LONUFAL, 1400), (Soldier.KAHKLEH, 1182)],
                'path': [2, 3, 5, 8, 9]
            },
        ]), {'times':[(1,45), (14,50), (22,30)]}),
    ),
    (
        (Construct, (Building.HOUSE, 1)),
        (Construct, (Building.UNIVERSITY, 1))
    ),
    (
        (Construct, (Building.FARM, 5)),
        (Construct, (Building.SAWMILL, 5)),
        (Construct, (Building.FACILITY_CENTER, 6)),
        (Study, (Tech.FORGING, 3))
    ),
    (
        (Construct, (Building.FARM, 20)),
        (Construct, (Building.HOUSE, 21)),
        (Study, (Tech.FORGING, 20))
    ),
    (
        (Study, (Tech.ATTACK_FORMATION, 20), {'university': 20}),
        (Study, (Tech.DEFENSE_FORMATION, 20, 22))
    )
)
