import logging
import unittest

from emross.utility.player import Player
from test import bot

logger = logging.getLogger(__name__)

class TestPlayer(unittest.TestCase):
    def setUp(self):
        self.bot = bot
        self.player = Player('s1.emrosswar.com')

    def test_attribute_lookup(self):
        self.assertEqual(0, self.player.get('fake', 0))

        self.player.fake = 1
        self.assertEqual(1, self.player.get('fake', 0))

    def test_kwargs(self):
        player = Player('s1.emrosswar.com', custom=123, **{'unpacked': 0})
        self.assertEqual(123, player.custom)
        self.assertEqual(None, player.nothing)
        self.assertNotEqual(None, player.unpacked)

    def test_playtimes(self):
        self.assertEqual([(-1, 25)], self.player.playtimes)

        player = Player('s1.emrosswar.com', playtimes=[])
        self.assertNotEqual([(-1, 25)], player.playtimes)
