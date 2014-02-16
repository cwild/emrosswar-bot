import unittest

from emross import mobs
from emross.arena.hero import Gear, Hero
from emross.military.camp import Soldier
from emross.utility.calculator import WarCalculator


mobs.commanders = [
    mobs.Hero('ChaosLord', attack=30, defense=15)
]
mobs.units = [
    mobs.Unit('Horror',critical=100),
    mobs.Unit('Nightmare',critical=200),
    mobs.Unit('Inferno',critical=400),
]

from test import bot


class TestDefenseCalculation(unittest.TestCase):

    def setUp(self):
        self.calculator = WarCalculator(bot)

        self.comboes = [
            ({
                'hero': Hero({Hero.ATTACK: 172, Hero.WISDOM: 35, Hero.DEFENSE: 39,}),
                'troops': {Soldier.KAHKLEH: 250},
            }, (235305, 817031, 2042578)),
            ({
                'hero': Hero({Hero.ATTACK: 314, Hero.WISDOM: 48, Hero.DEFENSE: 217,},
                gear={
                    Gear.ARMOR_SLOT: {'item': {'up': 38, 'attr': [0, 24080, 0, 0, 0, 0], 'num': 1, 'id': '1791913', 'sid': '27'}, 'id': '393490'}
                }),
                'troops': {Soldier.KAHKLEH: 3042},
            }, (5451494, 14205759, 35514399)),
        ]

    def test_attack(self):
        for kwargs, outcome in self.comboes:
            defense, min_attack, max_attack = outcome
            self.assertEqual(self.calculator.attack(**kwargs), (min_attack, max_attack))

    def test_defense(self):
        for kwargs, outcome in self.comboes:
            defense, min_attack, max_attack = outcome
            self.assertEqual(self.calculator.defense(**kwargs), defense)
