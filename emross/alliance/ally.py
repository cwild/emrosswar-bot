from emross.api import EmrossWar
from emross.utility.base import EmrossBaseObject

class Alliance(EmrossBaseObject):
    MAX_TECH_LEVEL = 5
    UNION_INFO = 'game/api_union_info.php'

    def __init__(self, bot):
        super(Alliance, self).__init__(bot, __name__)
        self._info = []
        self.id = None

    @property
    def in_ally(self):
        return self.bot.userinfo.get('guildid', 0) > 0

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
        json = self.bot.api.call(self.UNION_INFO, op='info')

        if json['code'] == EmrossWar.SUCCESS:
            self._info = json['ret']
