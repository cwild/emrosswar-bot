import unittest

from emross import mobs
from emross.arena.hero import Gear, Hero
from emross.military.camp import Soldier
from emross.utility.calculator import WarCalculator


mobs.commanders = [
    mobs.Hero('ChaosLord', attack=30, defense=15)
]
mobs.units = [
    mobs.Unit('Horror', mobs.DevilArmy.SIX_STAR, attack=15, defense=8, critical=180),
    mobs.Unit('Nitemare', mobs.DevilArmy.SIX_STAR, attack=40, defense=12, critical=317.5),
    mobs.Unit('Inferno', mobs.DevilArmy.EIGHT_STAR, attack=120, defense=40, critical=120),
]

from test import bot


class TestDefenseCalculation(unittest.TestCase):

    def setUp(self):
        self.calculator = WarCalculator(bot)

        self.player_comboes = [
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


        # Apparently, the NPC hero has no effect on the calculations
        self.npc_comboes = [
            ({
                'hero': None,
                'hero_base': 0,
                'troops': {
                    mobs.Unit.find('Horror', mobs.DevilArmy.SIX_STAR): 500,
                    mobs.Unit.find('Nitemare', mobs.DevilArmy.SIX_STAR): 5000,
                },
                'ally': mobs.alliance,
                'soldier_data': mobs.Unit.soldier_data
            }, (64000, 207500, 648500)),
            ({
                'hero': None,
                'hero_base': 0,
                'troops': {
                    mobs.Unit.find('Horror', mobs.DevilArmy.SIX_STAR): 5452,
                },
                'ally': mobs.alliance,
                'soldier_data': mobs.Unit.soldier_data
            }, (43616, 81780, 147204)),
        ]

    def test_player_attack(self):
        for kwargs, outcome in self.player_comboes:
            defense, min_attack, max_attack = outcome
            self.assertEqual(self.calculator.attack(**kwargs), (min_attack, max_attack))

    def test_player_defense(self):
        for kwargs, outcome in self.player_comboes:
            defense, min_attack, max_attack = outcome
            self.assertEqual(self.calculator.defense(**kwargs), defense)

    def test_npc_attack(self):
        for kwargs, outcome in self.npc_comboes:
            defense, min_attack, max_attack = outcome
            self.assertEqual(self.calculator.attack(**kwargs), (min_attack, max_attack))

    def test_npc_defense(self):
        for kwargs, outcome in self.npc_comboes:
            defense, min_attack, max_attack = outcome
            self.assertEqual(self.calculator.defense(**kwargs), defense)

    def test_unknown_npc_unit(self):
        self.assertRaises(ValueError, mobs.Unit.find,
            'Unknown_NPC', mobs.DevilArmy.EIGHT_STAR
        )