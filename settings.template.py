from emross.military.camp import Soldier
from emross.mobs import DevilArmy

import logging
log_level = logging.DEBUG

logfile = '/tmp/emross.log'

session_path = 'build/session.pickle'

api_key = ''
pushid = ''

user_agent = 'Mozilla/5.0 (iPhone; U; CPU iPhone OS 4_3_2 like Mac OS X; en-us) AppleWebKit/533.17.9 (KHTML, like Gecko) Mobile/8H7'

game_server = 'YOURSERVER.emrosswar.com'

get_heroes = 'game/gen_conscribe_api.php'
get_soldiers = 'game/soldier_educate_api.php'

hero_conscribe = 'game/gen_conscribe_api.php'


api_fav = 'game/api_fav.php'


"""Id = 12553, name = crow tree
--Id = 21111, name = localhost
Id = 21261, name = 127001
Id = 21469, name = Meadery
Id = 21824, name = Sparta
Id = 22008, name = Reboot"""
ignore_cities = [22008]


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



# If this comes up then we should hire it
enable_recruit = False
recruit_heroes = [1, 2, 3, 4]

prefer_closer = True

"""
You can set the times at which you would like to farm here.

The default is all day. You can set multiple ranges here though. eg.
[(6, 9), (15, 18), (22, 23)]
"""
farming_hours = [(-1, 25)]


"""
Alliance donations? Remove the below if you don't want donations enabled.
You can reorder the donation preferences as you like
"""

from emross.alliance import Alliance as AT

donation_tech_preference = [AT.VETERAN, AT.VALOR, AT.TENACITY, AT.INCENTIVE, AT.TOUGHNESS,
    AT.INSPIRATION, AT.BATTLECRY, AT.MILICADEMY, AT.BLOODFLAG]


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

from emross.utility.task import Task

class MyTask(Task):
    def process(self, a=1, b=2, gems=0, *args, **kwargs):
        print 'my task run', args, kwargs
        print a, b, gems

build_path = (
    (
        (MyTask, (5, 6), {'gems':100}),
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
    )
)