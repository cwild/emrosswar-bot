import unittest

from emross.arena.hero import Hero
from emross.arena.visit import HeroVisit

class TestArenaVisit(unittest.TestCase):

    def setUp(self):
        self.visit = HeroVisit(None)

    def test_hero_parsing(self):
        heroes = self.visit.split_heroes('172|d|1,68|c|4')
        current = self.visit.calculate_components( [(Hero(h).client['rank'], Hero(h).client['race']) for h in heroes] )
        expected = {'c': {4: 1}, 'd': {1: 1}}
        self.assertEqual(current, expected)
        self.assertTrue(self.visit.compare_heroes(current, expected))

    def test_ladies(self):
        cur = {Hero.QUEEN: {'*': 2}}
        self.assertEqual('2_c', self.visit.reward_conversion(cur))

    def test_jqk(self):
        self.assertEqual('3_b_c_d', self.visit.reward_conversion({
            Hero.JACK: {'*': 1},
            Hero.QUEEN: {'*': 1},
            Hero.KING: {'*': 1}
        }))

    def test_three_of_a_kind(self):
        reward = '3_same'
        convert = self.visit.reward_conversion
        self.assertEqual(reward, convert({Hero.TEN: {'*': 3}}))
        self.assertEqual(reward, convert({Hero.JACK: {'*': 3}}))
        self.assertEqual(reward, convert({Hero.QUEEN: {'*': 3}}))
        self.assertEqual(reward, convert({Hero.KING: {'*': 3}}))
        self.assertEqual(reward, convert({Hero.ACE: {'*': 3}}))

    def test_four_of_a_kind(self):
        reward = '4_same'
        convert = self.visit.reward_conversion
        self.assertEqual(reward, convert({Hero.TEN: {'*': 4}}))
        self.assertEqual(reward, convert({Hero.JACK: {'*': 4}}))
        self.assertEqual(reward, convert({Hero.QUEEN: {'*': 4}}))
        self.assertEqual(reward, convert({Hero.KING: {'*': 4}}))
        self.assertEqual(reward, convert({Hero.ACE: {'*': 4}}))

    def test_two_pairs(self):
        reward = '4_double'
        convert = self.visit.reward_conversion
        self.assertEqual(reward, convert({Hero.JACK: {'*': 2}, Hero.TEN: {1: 2}}))
        self.assertEqual(reward, convert({Hero.QUEEN: {'*': 2}, Hero.JACK: {1: 2}}))
        self.assertEqual(reward, convert({Hero.KING: {'*': 2}, Hero.QUEEN: {1: 2}}))
        self.assertEqual(reward, convert({Hero.ACE: {'*': 2}, Hero.KING: {1: 2}}))

    def test_five_of_a_kind(self):
        reward = '5_same'
        convert = self.visit.reward_conversion
        self.assertEqual(reward, convert({Hero.TEN: {'*': 5}}))
        self.assertEqual(reward, convert({Hero.JACK: {'*': 5}}))
        self.assertEqual(reward, convert({Hero.QUEEN: {'*': 5}}))
        self.assertEqual(reward, convert({Hero.KING: {'*': 5}}))
        self.assertEqual(reward, convert({Hero.ACE: {'*': 5}}))

    def test_straight(self):
        reward = self.visit.reward_conversion({
            Hero.TEN: {Hero.HEARTS: 1},
            Hero.JACK: {Hero.CLUBS: 1},
            Hero.QUEEN: {Hero.SPADES: 1},
            Hero.KING: {Hero.DIAMONDS: 1},
            Hero.ACE: {Hero.HEARTS: 1}
        })
        self.assertEqual('5_different', reward)

    def test_full_house(self):
        reward = self.visit.reward_conversion({
            Hero.ACE: {Hero.DIAMONDS: 3},
            Hero.JACK: {Hero.CLUBS: 2}
        })
        self.assertEqual('5_three', reward)

    def test_royal_flush(self):
        reward = self.visit.reward_conversion({
            Hero.TEN: {Hero.HEARTS: 1},
            Hero.JACK: {Hero.HEARTS: 1},
            Hero.QUEEN: {Hero.HEARTS: 1},
            Hero.KING: {Hero.HEARTS: 1},
            Hero.ACE: {Hero.HEARTS: 1}
        })
        self.assertEqual('5_all_same', reward)

if __name__ == '__main__':
    unittest.main()