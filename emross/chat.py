import time

from emross.utility import events
from emross.utility.parser import (MessageParser,
    MessageParsingError, SkipMessage)
from emross.utility.task import Task

class Channel:
    ALLIANCE = 1
    PRIVATE = 2
    WORLD = 0

class ChatEvent:
    NEW_CASTLE = 1
    NEW_MAIL = 2
    RELOAD_CITY = 3
    RESYNC_USER = 4
    RECEIEVED_TEXT = 5
    GIFT_AVAILABLE = 6
    COUNTDOWN_RELOAD = 7
    SYSTEM_UPDATE = 8


class Chat(Task):
    INTERVAL = 5
    URL = 'game/api_chat2.php'

    def setup(self):
        try:
            self.lineid = self.bot.session.chat_id
        except AttributeError:
            self.lineid = -1

        self.bot.events.subscribe('ping', self.ping)
        self.bot.events.subscribe('spam', self.spam)

    def process(self):
        json = self.bot.api.call(self.URL, lineid=self.lineid)

        try:
            self.parse_events(json['ret']['evt'])
            self.parse_messages(json['ret']['msg'])
        except (AttributeError, IndexError) as e:
            self.log.exception(e)


    def parse_messages(self, messages):
        """
        The messages are both in-game chat and the activity feed
        """
        targets = [self.bot.userinfo.get('nick', '')]
        if self.bot.api.player:
            targets.append(self.bot.api.player.username)

        for msg in messages[::-1]:
            try:
                self.lineid = msg['line_id']
                text = msg.get('line_txt')
                if text and msg.get('from_name') in self.bot.operators:
                    method, args, kwargs = MessageParser.parse_message(text, targets)
                    self.bot.events.notify(method, *args, **kwargs)
            except SkipMessage:
                pass
            except MessageParsingError:
                pass
            except Exception as e:
                self.log.exception(e)

        self.bot.session.chat_id = self.lineid

    def parse_events(self, messages):
        """
        The message may contain useful info such as incoming loot notifcations.
        Maybe we can use this in future.
        """
        try:
            for msg in messages[::-1]:
                _type = msg.get('typeid')
                if _type == ChatEvent.COUNTDOWN_RELOAD:
                    pass

        except Exception as e:
            self.log.exception(e)


    def ping(self, *args, **kwargs):
        self.send_message('pong')

    def send_message(self, message, channel=Channel.ALLIANCE, **kwargs):
        can_send = False

        if channel == Channel.ALLIANCE:
            guild_id = self.bot.userinfo.get('guildid')
            if guild_id:
                target, can_send = guild_id, True

        if can_send:
            self.bot.api.call(self.URL, txt=message, targettype=channel, targetid=target)

    def spam(self, *args, **kwargs):
        msg = kwargs.get('delim', ' ').join(args)
        for i in range(int(kwargs.get('times', 1))):
            self.send_message(msg, channel=kwargs.get('channel', Channel.ALLIANCE))

        pass
        #logger.debug(message)
