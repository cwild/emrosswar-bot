import re
import time

from emross.api import EmrossWar
from emross.utility.controllable import Controllable
from emross.utility.task import Task


class FarmMonitor(Controllable, Task):
    COMMAND = 'farm-monitor'
    INTERVAL = 30

    DEFAULT_MINUTE_WINDOW = 30
    EXPIRY_PERIOD = 86400
    NPC = 'DevilArmy'
    PATTERN = '<b>(.*)</b>'

    def setup(self):
        # Create the regex we are looking for with this monitor
        self.regex = re.compile('{0} defeats {1}'.format(self.PATTERN, self.NPC))

        try:
            self.store = self.bot.session.farm_monitor
        except AttributeError:
            self.store = self.bot.session.farm_monitor = {}

        self.bot.events.subscribe('scroll_activity', self.monitor)

    def process(self, *args, **kwargs):
        threshold = time.time() - self.EXPIRY_PERIOD

        for player, data in self.store.iteritems():
            if 'activity' in data:
                data['activity'][:] = [a for a in data.get('activity', []) if a > threshold]

    def monitor(self, event, message, *args, **kwargs):

        r = self.regex.match(message)
        if r:
            player = r.groups()[0]
            self.log.debug('Farm activity for "{0}"'.format(EmrossWar.safe_text(player)))
            self.store.setdefault(player, {}).setdefault('activity', []).append(time.time())

    def action_activity(self, event, minutes=DEFAULT_MINUTE_WINDOW, *args, **kwargs):
        """
        How many people have farmed in the last "minutes" (default=30)
        """

        total = 0
        threshold = time.time() - (60 * int(minutes))

        for player, data in self.store.iteritems():
            if [a for a in data.get('activity', []) if a > threshold]:
                total += 1

        if total == 0:
            self.chat.send_message('Not many active farmers, eh!')
            return

        self.chat.send_message(
            'Farming activity: {0} players in the last {1} {2}'.format(\
                total, minutes, 'minute' if minutes == 1 else 'minutes')
        )

    def action_busiest(self, event, n=5, minutes=DEFAULT_MINUTE_WINDOW, *args, **kwargs):
        """
        Who are the "n" busiest farmers in the last "minutes"?
        """

        busiest = []
        threshold = time.time() - (60 * int(minutes))
        n = int(n)

        for player, data in self.store.iteritems():
            busiest.append((player, len([a for a in data.get('activity', []) if a > threshold])))

        busiest.sort(key = lambda el: el[1], reverse=True)
        self.log.debug(busiest)

        parts = []
        for player, times in busiest[0:n]:
            if times:
                parts.append(u'{0}({1})'.format(player, times))

        self.chat.send_message('{0} busiest farmers in last {1} {2}: {3}'.format(\
            n, minutes, 'minute' if minutes == 1 else 'minutes',
            EmrossWar.safe_text(', '.join(parts))
        ))
