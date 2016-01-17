from test import bot, unittest

import emross
from emross.api import EmrossWar
from emross.resources import Resource

class ResourcesTester(unittest.TestCase):

    def setUp(self):
        city = bot.cities[0]
        self.resource_manager = city.resource_manager

    @emross.defer.inlineCallbacks
    def test_multiples(self):
        cost_per_item = {
            Resource.GOLD: 1500,
            Resource.WOOD: 4500,
            Resource.IRON: 4500,
            Resource.FOOD: 1500,
        }
        result = yield self.resource_manager.calculate_multiples(cost_per_item)
        self.assertEqual(result, 12)

    @emross.defer.inlineCallbacks
    def test_dummy_brick_conversion(self):

        cur_gold = yield self.resource_manager.get_amount_of(Resource.GOLD)
        self.resource_manager.set_amount_of(Resource.GOLD, 59999)

        # Bricks
        result = yield self.resource_manager.calculate_multiples({Resource.GOLD: 10000})
        self.assertEqual(result, 5)

        # Bullion
        result = yield self.resource_manager.calculate_multiples({Resource.GOLD: 1000})
        self.assertEqual(result, 59)

        # restore gold
        self.resource_manager.set_amount_of(Resource.GOLD, cur_gold)
