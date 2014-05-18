import unittest

from emross.military.camp import Soldier
from emross.military.defender import Aggressor

class TestAutoDefense(unittest.TestCase):

    def setUp(self):
        from test import bot
        city = bot.cities[0]


    def test_defendable(self):
        aggressor = Aggressor({Soldier.KAHKLEH: (100,200)})
        incoming = {Soldier.OVERLORD: 1, Soldier.LONUFAL: 1, Soldier.SPY: 1}
        self.assertEqual(True, aggressor.defendable(incoming))
