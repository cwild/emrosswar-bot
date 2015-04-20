import unittest

from collections import defaultdict

from emross.arena.hero import Hero
from emross.arena.fighter import ArenaFighter, TargetManager

from test import bot

TEST_WORLD = 'testing'

class TestArenaFighter(unittest.TestCase):

    def setUp(self):
        self.fighter = ArenaFighter(bot)
        self.manager = TargetManager()

    def test_world_creation(self):
        manager = TargetManager()

        self.assertTrue(len(manager.keys()) == 0, 'Too many game worlds')

        self.assertEqual(manager[TEST_WORLD], defaultdict())
        self.assertEqual(manager[TEST_WORLD].default_factory, list)

        self.assertTrue(len(manager.keys()) == 1, 'Not enough game worlds')
        self.assertEqual(manager.keys(), [TEST_WORLD])


    def test_world_heroes(self):
        self.assertEqual(self.manager[TEST_WORLD][30], [])
        self.manager[TEST_WORLD][30].extend([1, 2, 3])
        self.assertEqual(self.manager[TEST_WORLD][30], [1, 2, 3])


if __name__ == '__main__':
    unittest.main()
