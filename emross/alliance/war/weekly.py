from emross.api import EmrossWar
from emross.utility.task import Task

from lib import six


class WeeklyWar(Task):
    INTERVAL = 3600
    URL = 'game/union_week_api.php'

    # Status
    APPLIED = 1
    NOT_APPLIED = 2

    # Stages
    APPLYING = 1
    WAITING_FOR_RESULT = 2
    READY_FOR_BATTLE = 3
    BATTLE = None

    def process(self, auto_apply=True, *args, **kwargs):

        if not self.bot.alliance.in_ally:
            self.log.debug('Cannot participate in war without being in an alliance')
            return

        json = self.bot.api.call(self.URL, action='union_status')

        applicants = json['ret'].get('nums', 0)
        self.log.info('Allies that have applied for Weekly War: {0}'.format(applicants))

        status = json['ret'].get('status')

        if status == self.APPLIED:
            self.log.info('Already applied for Weekly Ally War')

        if json['ret'].get('power', 0) == 1:

            if auto_apply and status == self.NOT_APPLIED:
                self.apply_for_war()

    def apply_for_war(self):
        json = self.bot.api.call(self.URL, action='union_apply')
        if json['code'] == EmrossWar.SUCCESS:
            self.log.info(six.u('"{0}" has applied for weekly ally war').format(\
                self.bot.userinfo.get('guild', '')
            ))

        return json

    def cancel_war(self):
        self.bot.api.call(self.URL, action='union_apply_cancel')
