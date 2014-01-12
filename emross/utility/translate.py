# coding: utf-8
import urllib
import sys
import time

from lib.goslate import goslate

from emross.api import EmrossWar
from emross.utility.controllable import Controllable
from emross.utility.task import Task
from emross.world import World

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

    def action_add(self, player=None, lang='en', *args, **kwargs):
        """
        Add a player who we wish to autotranslate for.
        """
        if player:
            self.translate_for[player] = lang

        x, y = kwargs.get('x'), kwargs.get('y')
        if x and y:
            name = self.player_at(x, y)

            if name:
                self.translate_for[name] = lang
                self.chat.send_message(EmrossWar.safe_text(
                    u'Translating "{0}" to "{1}"!'.format(name, lang)
                ))

    def action_list(self, *args, **kwargs):
        """
        List the players to translate for.
        """
        self.chat.send_message(EmrossWar.safe_text(', '.join(
            [u'{0}({1})'.format(k,v) for k, v in self.translate_for.iteritems()]
        )))

    def action_remove(self, player=None, *args, **kwargs):
        """
        Add a player who we wish to autotranslate for.
        """
        try:
            if player:
                del self.translate_for[player]
            else:
                x, y = kwargs.get('x'), kwargs.get('y')
                if x and y:
                    name = self.player_at(x, y)
                    del self.translate_for[name]
                    self.chat.send_message(EmrossWar.safe_text(
                        u'Stopped translating for "{0}".'.format(name)
                    ))
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

    def action_wake(self, *args, **kwargs):
        """
        Wakey, wakey. Rise and shine!
        """
        self._mute_period = time.time()

    def player_at(self, x, y):
        world = self.bot.builder.task(World)
        node = world.get_point(x, y)

        if node and node[2] == World.PLAYER_NODE:
            return node[3][1]

    def translate(self, text, *args, **kwargs):
        player = kwargs['meta-data'].get('name')
        target_lang = self.translate_for.get(player)

        if target_lang and self._mute_period < time.time():
            self.log.debug(text)
            converted = TRANSLATOR.translate(text, target_lang)

            if text == converted:
                self.log.debug('Converted text is the same, no need to repeat')
                return

            converted = EmrossWar.safe_text(converted)
            self.log.debug(converted)

            self.chat.send_message(converted,
                prefix=EmrossWar.safe_text(u'{0} said: '.format(player))
            )

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
