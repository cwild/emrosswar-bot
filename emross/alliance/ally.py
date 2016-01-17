import time

import emross
from emross.api import EmrossWar
from emross.alliance import ALLIANCE_INFO_URL, ALLIANCE_URL
from emross.utility.controllable import Controllable

from lib.cacheable import CacheableData

RANK_LEADER = 1
RANK_OFFICER = 3
RANK_MEMBER = 5

class Alliance(Controllable, CacheableData):
    COMMAND = 'ally'
    MAX_TECH_LEVEL = 5

    def __init__(self, bot):
        super(Alliance, self).__init__(bot, cache_data_type=list)
        self.id = None
        self._time = None

    @property
    @emross.defer.inlineCallbacks
    def in_ally(self):
        userinfo = yield self.bot.userinfo
        guildid = userinfo.get('guildid', 0)

        if self._time is None and guildid:
            self._time = time.time()

        emross.defer.returnValue(guildid > 0)

    @emross.defer.inlineCallbacks
    def info(self, **kwargs):
        json = yield self.bot.api.call(ALLIANCE_INFO_URL, **kwargs)
        emross.defer.returnValue(json)

    @property
    @emross.defer.inlineCallbacks
    def hall_tech(self):
        data = yield self.data
        emross.defer.returnValue(data[5])

    @emross.defer.inlineCallbacks
    def tech(self, tech):
        try:
            hall_tech = yield self.hall_tech
            state, level, cooldown = hall_tech[tech-1]
            self.log.debug('"{0}" is level {1}'.format(EmrossWar.LANG['ALLY_TECH'][str(tech)]['name'], level))
            emross.defer.returnValue(level)
        except (IndexError, KeyError, ValueError):
            emross.defer.returnValue(0)

    @emross.defer.inlineCallbacks
    def update(self):
        userinfo = yield self.bot.userinfo
        guildid = userinfo.get('guildid', 0)

        if guildid == 0:
            emross.defer.returnValue({})

        if guildid != self.id:
            # Only log if our alliance membership has changed
            if self.id is not None:
                self.log.debug('Not in the same alliance as previous check')

            # update the guildid
            self.id = guildid

            self.log.info('is a member of "{0}"'.format(
                EmrossWar.safe_text(userinfo.get('guild', ''))
            ))

        # If there is still some cooldown, do not cache the result
        elif self._data and set([(self.MAX_TECH_LEVEL, 0)]) == \
            set([(level, cooldown) for state, level, cooldown in self._data[5]]):
                self.log.debug('Maxed Alliance hall, reuse cached data')
                emross.defer.returnValue(self._data)

        self.log.debug('Update alliance hall info')
        json = yield self.bot.api.call(ALLIANCE_INFO_URL, op='info')
        emross.defer.returnValue(json)

    def action_cooldown(self, event, *args, **kwargs):
        """
        How much longer before I can receive troops?
        """

        if not self.in_ally:
            return

        json = self.info()
        if json['code'] == EmrossWar.SUCCESS:
            moved, quota, cooldown = json['ret'].get('quota', [0,0,0])
            msg = 'Quota: {0}/{1}, Cooldown: {2}'.format(moved, quota, \
                self.bot.human_friendly_time(cooldown))
            self.chat.send_message(msg, event=event)

    def action_join(self, event, *args, **kwargs):
        """
        Join the ally of the player who issued the command!
        Last available team unless specified otherwise.
        """
        if self.in_ally:
            return

        try:
            # Get player info
            json = self.bot.other_player_info(id=event.player_id)
            player = json['ret']['user']

            # Get alliance join info
            guildid = player['guildid']
            application_info = self.bot.api.call(ALLIANCE_URL, id=guildid)

            try:
                # We can provide a team number to apply to
                team = application_info['ret']['team'][int(kwargs.get('team'))]
            except (IndexError, TypeError):
                # or just use the last available team
                team = application_info['ret']['team'][-1]

            self.log.info('Apply to "{0}"'.format(EmrossWar.safe_text(team['name'])))

            self.bot.api.call(ALLIANCE_URL, id=guildid, tid=team['id'],
                info=' '.join(args))
        except KeyError:
            return

    @Controllable.restricted
    def action_quit(self, event, *args, **kwargs):
        """
        Quit the current alliance. Requires provision of a "password".
        """
        if not self.in_ally:
            return

        """
        If this is a command that was sent before we were in the ally then
        we should not respond as it wasn't aimed at us.
        """
        if self._time is None or event.data.get('time', time.time()) < self._time:
            return

        if self.bot.userinfo.get('gpower') == RANK_MEMBER:
            self.bot.api.call(ALLIANCE_INFO_URL, delid=self.bot.userinfo.get('id'))
        else:
            self.chat.send_message('I rank too high to simply quit!')
