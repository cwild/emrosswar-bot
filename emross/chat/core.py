import time

from emross.api import EmrossWar
from emross.chat.filter import PlayerFilter
from emross.handlers.handler import EmrossHandler
from emross.utility.events import Event
from emross.utility.parser import (MessageParser,
    MessageParsingError, SkipMessage)
from emross.utility.task import Task

class Channel:
    ALLIANCE = 1
    PRIVATE = 2
    WORLD = 0

CHANNELS = {
    EmrossWar.LANG['CHATCHANNEL']['0'].lower(): Channel.WORLD,
    EmrossWar.LANG['CHATCHANNEL']['1'].lower(): Channel.ALLIANCE,
    EmrossWar.LANG['CHATCHANNEL']['2'].lower(): Channel.PRIVATE,
}

class ChatEvent:
    NEW_CASTLE = 1
    NEW_MAIL = 2
    RELOAD_CITY = 3
    RESYNC_USER = 4
    RECEIVED_TEXT = 5
    GIFT_AVAILABLE = 6
    COUNTDOWN_RELOAD = 7
    SYSTEM_UPDATE = 8

class _OldChatApi(EmrossHandler):
    URL = 'game/api_chat.php'

    def process(self, errors):
        self.log.debug('Failed to send message, try the old chat API')
        self.log.debug((self.args, self.kwargs))
        return self.bot.api.call(self.URL, **self.kwargs)

class Chat(Task):
    INTERVAL = 5
    MAX_MESSAGE_LENGTH = 80
    URL = 'game/api_chat2.php'

    def setup(self):
        self.player_filter = PlayerFilter(self.bot)
        self.parsers = (
            ('evt', self.parse_events),
            ('msg', self.parse_messages),
        )

        self.bot.events.subscribe('ping', self.ping)
        self.bot.events.subscribe('spam', self.spam)

    @property
    def lineid(self):
        try:
            return self.bot.session.chat_id
        except AttributeError:
            return -1

    def process(self):
        json = self.bot.api.call(self.URL, lineid=self.lineid)

        for section, parser in self.parsers:
            try:
                if section in json['ret']:
                    parser(json['ret'][section])
            except (AttributeError, IndexError) as e:
                self.log.exception(e)

    def parse_messages(self, messages):
        """
        The messages are both in-game chat and the activity feed
        """
        targets = [self.bot.userinfo.get('nick', '')]
        if self.bot.api.player:
            targets.append(self.bot.api.player.username)
            targets.extend(self.bot.api.player.groups or [])

        for msg in messages[::-1]:
            try:
                self.bot.session.chat_id = msg['line_id']
                text = msg.get('line_txt')

                data = {
                    'player_id': msg.get('from_id'),
                    'player_name': msg.get('from_name'),
                    'channel': msg.get('target_type'),
                    'time': time.time()
                }

                if text and (msg.get('from_name') in self.bot.operators or \
                    msg.get('from_name') == self.bot.userinfo.get('nick')):

                    method, args, kwargs = MessageParser.parse_message(text, targets,
                        myself=msg.get('from_name') == self.bot.userinfo.get('nick'),
                        filter=self.player_filter.filter)

                    try:
                        data['channel'] = CHANNELS[kwargs['channel'].lower()]
                        del kwargs['channel']
                    except KeyError:
                        pass

                    event = Event(method, **data)
                    self.bot.events.notify(event, *args, **kwargs)

                elif msg.get('from_name') not in ('', self.bot.userinfo.get('nick')):
                    event = Event('chat_message', **data)
                    self.bot.events.notify(event, text)

                else:
                    event = Event('scroll_activity', **data)
                    self.bot.events.notify(event, text)
            except SkipMessage as e:
                self.log.debug(e)
            except MessageParsingError:
                event = Event('chat_message', **data)
                self.bot.events.notify(event, text)
            except Exception as e:
                self.log.exception(e)


    def parse_events(self, messages):
        """
        The message may contain useful info such as incoming loot notifcations.
        """
        try:
            for msg in messages[::-1]:
                event_type = msg.get('typeid')

                if event_type == ChatEvent.NEW_MAIL:
                    self.bot.events.notify(Event('mail.message.received'))

                elif event_type == ChatEvent.COUNTDOWN_RELOAD:
                    event = Event('city.countdown.reload')
                    self.bot.events.notify(event, city_id=int(msg['cid']))

                elif event_type in [ChatEvent.NEW_CASTLE, ChatEvent.RESYNC_USER]:
                    # update userinfo on next data access
                    self.bot.expire()

                elif event_type == ChatEvent.RECEIVED_TEXT:
                    self.log.info(msg['txt'])

        except Exception as e:
            self.log.exception(e)


    def ping(self, event, *args, **kwargs):
        self.send_message('pong', event=event)

    def send_message(self, message, prefix='', event=None, **kwargs):
        can_send = False

        try:
            channel = event.channel
        except AttributeError:
            channel = Channel.ALLIANCE

        if channel == Channel.ALLIANCE:
            guild_id = self.bot.userinfo.get('guildid')
            if guild_id:
                target, can_send = guild_id, True

        elif channel == Channel.PRIVATE:
            if event:
                target, can_send = event.player_id, True

        elif channel == Channel.WORLD:
            target, can_send = 0, True

        if can_send:
            """
            After the max message length, the remainder is discarded by the server!
            """
            prefix = prefix.encode('utf-8')
            size = self.MAX_MESSAGE_LENGTH - len(prefix)
            for letters in map(None, *(iter(message.encode('utf-8')),) * size):
                chunk = ''.join([l for l in letters if l is not None])

                self._send_message(self.URL,
                    txt=prefix+chunk,
                    targettype=channel, targetid=target)

    def _send_message(self, *args, **kwargs):
        """
        Try to work with the newer chat API, when it works..
        """
        handlers = {
            500: lambda c : _OldChatApi(c, args, kwargs)
        }
        return self.bot.api.call(http_handlers=handlers, *args, **kwargs)

    def spam(self, event, *args, **kwargs):
        msg = kwargs.get('delim', ' ').join(args)
        for i in range(int(kwargs.get('times', 1))):
            self.send_message(msg, event=event)
