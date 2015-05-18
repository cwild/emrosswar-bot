import logging
import unittest

from emross.utility.controllable import Controllable as _Controllable
from test import bot

logger = logging.getLogger(__name__)

class Controllable(_Controllable):
    COMMAND_PASSWORD = 'testing'


class TestControllable(unittest.TestCase):
    def setUp(self):
        self.bot = bot

    def test_controllable_wrapper(self):
        task = self.bot.builder.task(Controllable)

        @Controllable.restricted
        def func(bot, *args, **kwargs):
            return kwargs


        a = func(task, tester=123, password='testing')
        b = func(task, password='testing')

        self.assertNotEqual(a.keys(), b.keys())
