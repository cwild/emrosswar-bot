import logging
import unittest

from emross.utility.parser import MessageParser

from test import bot


logger = logging.getLogger(__name__)

class TestMessageParser(unittest.TestCase):
    def setUp(self):
        #self.bot = bot
        self.messages = [
            ('ping',"""!ping"""),
            ('ping',"""!{x,y,level=1}ping"""),
        ]

    def test_message_parser(self):
        for command, message in self.messages:
            method_name, args, kwargs = MessageParser.parse_message(message)
            self.assertEqual(command, method_name)
