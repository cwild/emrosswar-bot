import time

from emross.api import EmrossWar
from emross.alliance import ALLIANCE_INFO_URL, ALLIANCE_URL
from emross.utility.controllable import Controllable

RANK_LEADER = 1
RANK_OFFICER = 3
RANK_MEMBER = 5

class Alliance(Controllable):
    COMMAND = 'ally'
    COMMAND_PASSWORD = None
    MAX_TECH_LEVEL = 5

    def __init__(self, bot):
        super(Alliance, self).__init__(bot)
        self._info = []
        self.id = None
        self._time = None

    @property
    def in_ally(self):
        guildid = self.bot.userinfo.get('guildid', 0)

        if self._time is None and guildid:
            self._time = time.time()

        return guildid > 0

    @property
    def info(self):
        if not self._info:
            self.update()
        return self._info

    @property
    def hall_tech(self):
        return self.info[5]

    def tech(self, tech):
        try:
            state, level, cooldown = self.hall_tech[tech-1]
            self.log.debug('"{0}" is level {1}'.format(EmrossWar.LANG['ALLY_TECH'][str(tech)]['name'], level))
            return level
        except (IndexError, ValueError):
            return 0

    def update(self):
        guildid = self.bot.userinfo.get('guildid', 0)

        if guildid != self.id:
            # Only log if our alliance membership has changed
            if self.id is not None:
                self.log.debug('Not in the same alliance as previous check')

            # update the guildid
            self.id = guildid

        if self.id == 0:
            return

        ally = self.bot.userinfo.get('guild', '').encode('utf-8')
        self.log.info('is a member of "{0}"'.format(ally))

        self.log.debug('Update alliance hall info')
        json = self.bot.api.call(ALLIANCE_INFO_URL, op='info')

        if json['code'] == EmrossWar.SUCCESS:
            self._info = json['ret']


    def action_join(self, *args, **kwargs):
        """
        Join the ally of the player who issued the command!
        Last available team unless specified otherwise.
        """
        if self.in_ally:
            return

        try:
            # Get player info
            json = self.bot.other_player_info(id=kwargs['meta-data']['id'])
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

    def action_quit(self, *args, **kwargs):
        """
        Quit the current password. Requires provision of a "password".
        """
        if not self.in_ally:
            return

        """
        If this is a command that was sent before we were in the ally then
        we should not respond as it wasn't aimed at us.
        """
        if self._time is None or kwargs.get('time', time.time()) < self._time:
            return

        password = kwargs.get('password')

        if password and self.COMMAND_PASSWORD:

            # Password present but must match
            if self.COMMAND_PASSWORD.lower() == password.lower():

                if self.bot.userinfo.get('gpower') == RANK_MEMBER:
                    self.bot.api.call(ALLIANCE_INFO_URL, delid=self.bot.userinfo.get('id'))
                else:
                    self.chat.send_message('I rank too high to simply quit!')
            else:
                self.chat.send_message('No, I am quite happy staying here.')
