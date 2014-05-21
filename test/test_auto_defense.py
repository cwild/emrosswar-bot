import unittest

from emross.military.camp import Soldier
from emross.military.defender import Aggressor, AutoDefense

class TestAutoDefense(unittest.TestCase):

    def setUp(self):
        from test import bot
        self.defender = AutoDefense(bot)


    def test_defendable(self):
        aggressor = Aggressor({Soldier.KAHKLEH: (100,200)})
        incoming = {Soldier.OVERLORD: 1, Soldier.LONUFAL: 1, Soldier.SPY: 1}
        self.assertEqual(False, aggressor.defendable(incoming))

    def test_using_defensive_units(self):
        aggressor = Aggressor({
                Soldier.KAHKLEH: (0,200),
                Soldier.ASSASSIN: (1,200)
            },
            {Soldier.KAHKLEH: 1234}
        )

        incoming = {Soldier.ASSASSIN: 1, Soldier.MASTER: 30000}

        self.assertEqual(False, aggressor.defendable(incoming, available=[
            [Soldier.LONUFAL, 150], [Soldier.KAHKLEH, 1250]
        ]))

        aggressor.permit_unknown = True
        self.assertEqual(True, aggressor.defendable(incoming, available=[
            [Soldier.LONUFAL, 150], [Soldier.KAHKLEH, 1250]
        ]))

    def test_multiple_aggressors(self):
        available = [[Soldier.LONUFAL, 1500], [Soldier.KAHKLEH, 2500]]
        incoming = {Soldier.SPY: 501, Soldier.KAHKLEH: 3000}

        aggressors = [
            (False, Aggressor({Soldier.LONUFAL: (0, 1000), Soldier.KAHKLEH: (1, 2000)})),
            (False, Aggressor({Soldier.SPY: (0, 1500)})),
            (True, Aggressor({Soldier.SPY: (0, 1500)}, permit_unknown=True)),
            (False, Aggressor({Soldier.KAHKLEH: (2, 15)})),
            (False, Aggressor({Soldier.KAHKLEH: (1500, 2000)}, minimum_defensive_units={Soldier.MASTER: 1000})),
            (True, Aggressor({Soldier.KAHKLEH: (1500, 3000), Soldier.SPY: (0, 600)}, minimum_defensive_units={Soldier.LONUFAL: 1000})),
            (True, Aggressor({Soldier.SPY: (0, 501), Soldier.KAHKLEH: (1, 3000)})),
            (False, Aggressor({Soldier.SPY: (0, 501), Soldier.KAHKLEH: (1, 3000)}, defend=False)),
        ]

        for expected, aggressor in aggressors:
            self.assertEqual(expected, aggressor.defendable(incoming, available))
