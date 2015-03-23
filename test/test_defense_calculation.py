import logging
import time
import unittest

from emross import mobs
from emross.arena.hero import Gear, Hero
from emross.military.camp import Soldier
from emross.utility.calculator import WarCalculator

from test import bot

logger = logging.getLogger(__name__)


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
                'soldier_data': mobs.Unit.soldier_data,
                'assume_default_soldier_stats': False
            }, (64000, 207500, 648500)),
            ({
                'hero': None,
                'hero_base': 0,
                'troops': {
                    mobs.Unit.find('Horror', mobs.DevilArmy.SIX_STAR): 5452,
                },
                'ally': mobs.alliance,
                'soldier_data': mobs.Unit.soldier_data,
                'assume_default_soldier_stats': False
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

    def test_troops_required(self):
        start = time.time()

        num = self.calculator.troops_to_defend_attack(Soldier.KAHKLEH, 9876543210,
                hero=Hero({
                        Hero.ATTACK: 172,
                        Hero.WISDOM: 35,
                        Hero.DEFENSE: 39
                    })
                )

        finish = time.time()
        duration = finish - start

        self.assertEqual(num, 10495796)
        self.assertTrue(duration < 1, msg='Calculation took a long time')

    def test_unspecified_troops(self):
        num = self.calculator.troops_to_defend_attack(Soldier.HUNTER, 100000,
                hero=Hero({
                        Hero.ATTACK: 172,
                        Hero.WISDOM: 35,
                        Hero.DEFENSE: 39
                    })
                )

        self.assertEqual(num, 1021)

    def test_hit_points(self):
        hero = Hero({
            Hero.ATTACK: 31,
            Hero.WISDOM: 70,
            Hero.DEFENSE: 40
        })
        army = {Soldier.OVERLORD: 11}

        num = self.calculator.troops_to_defend_attack(Soldier.OVERLORD, 7500,
                hero=hero)

        self.assertEqual(self.calculator.defense(**{
            'hero': hero,
            'troops': army
        }), 7796)

        self.assertEqual(num, 11)

        player = {'hero':hero, 'troops':army}
        hostile = {
            'hero': None,
            'hero_base': 0,
            'troops': {mobs.Unit.find('Infantry', mobs.Colony.LARGE_FARM): 500},
            'assume_default_soldier_stats': False,
            'ally': mobs.alliance,
            'soldier_data': mobs.Unit.soldier_data,
        }

        for round, c1, c2 in self.calculator.battle_simulator(player, hostile):
            logger.debug((round, c1, c2))

        self.assertEqual(round, 6)

        # 500 infantry, 100 health each
        self.assertEqual(self.calculator.health(**hostile), 50000)
