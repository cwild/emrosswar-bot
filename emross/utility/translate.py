# coding: utf-8
import urllib
import sys
import time

from lib.goslate import goslate

from emross.api import EmrossWar
from emross.utility.controllable import Controllable
from emross.utility.task import Task

TRANSLATOR = goslate.Goslate()

class AutoTranslate(Task, Controllable):
    """
    Listen to chat messages
    """
    COMMAND = 'translate'
    SLEEP_DURATION = 3600

    def setup(self):
        self._mute_period = time.time()
        try:
            self.translate_for = self.bot.session.translate_for
        except AttributeError:
            self.translate_for = self.bot.session.translate_for = dict()

        self.bot.events.subscribe('chat_message', self.translate)

    def action_add(self, player=None, lang='en'):
        """
        Add a player who we wish to autotranslate for.
        """
        if player:
            self.translate_for[player] = lang

    def action_list(self):
        """
        List the players to translate for.
        """
        self.chat.send_message(', '.join(
            ['{0}({1})'.format(k,v) for k, v in self.translate_for.iteritems()]
        ))

    def action_remove(self, player=None):
        """
        Add a player who we wish to autotranslate for.
        """
        try:
            del self.translate_for[player]
        except KeyError:
            pass

    def action_sleep(self, seconds=SLEEP_DURATION, *args, **kwargs):
        """
        Number of `seconds` to be muted. I will not translate during this time.
        """
        try:
            delay = int(seconds)
        except (TypeError, ValueError):
            delay = self.SLEEP_DURATION

        self._mute_period = time.time() + delay

    def action_wake(self):
        """
        Wakey, wakey. Rise and shine!
        """
        self._mute_period = time.time()

    def translate(self, player, text, *args, **kwargs):

        target_lang = self.translate_for.get(player)
        if target_lang and self._mute_period < time.time():
            self.log.debug(text)
            converted = TRANSLATOR.translate(text, target_lang)

            self.log.debug(converted)
            converted = EmrossWar.safe_text(converted)
            self.log.debug(converted)

            self.chat.send_message(converted, prefix=u'{0} said: '.format(player))

    def process(self, players=[], *args, **kwargs):

        for player, lang in players:
            self.translate_for[player] = lang

        def _dummy(*args, **kwargs):
            pass
        self.process = _dummy

if __name__ == "__main__":
    #print TRANSLATOR.translate('hello world', 'fr')
    # test test spät
    # test%2520test%2520sp%25E4t

    from bot import bot
    bot.update()
    translate = AutoTranslate(bot)
    translate.action_add('tester', 'en')
    translate.translate('tester',u'wie spät ist es?')
