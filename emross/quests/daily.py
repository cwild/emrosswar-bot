from emross.api import EmrossWar
from emross.utility.task import Task

EmrossWar.extend('MISSION', 'translation/%(lang)s/mission_data.js')

NEW = 1
DONE = 3
ACCEPTED = 2
COMPLETE = 4


class DailyMissions(Task):
    INTERVAL = 600
    URL = 'game/daily_mission.php'

    OUT_OF_TURNS = 2201

    def setup(self):
        self.bot.events.subscribe('emross.gift.daily.received', lambda _: self.reschedule())

    def accept(self, mission):
        return self.bot.api.call(self.URL, action='accept', id=mission)

    def list(self):
        return self.bot.api.call(self.URL, action='list')

    def refresh(self):
        """
        This action costs gems.
        """
        return self.bot.api.call(self.URL, action='refresh')

    def reward(self, mission):
        return self.bot.api.call(self.URL, action='reward', id=mission)

    def process(self, *args, **kwargs):
        # We need to go at least once!
        running = True

        while running:
            # Don't go again unless we need to
            running = False

            missions = self.list()['ret']

            for mission in missions:
                data = EmrossWar.MISSION[mission['mid']]

                self.log.debug('"{0} {name}": {description} ({done}/{totaltimes})'.format(\
                    EmrossWar.LANG['MISSION_LANGUAGE']['DAILY'],
                    done=mission['done'], **data
                ))

                status = int(mission['status'])

                if status == NEW:
                    json = self.accept(mission['id'])

                    if json['code'] == EmrossWar.SUCCESS:
                        # Let's go again!
                        running = True
                    elif json['code'] == self.OUT_OF_TURNS:
                        self.log.debug('No more turns remain')
                        self.sleep(3600)
                        break
                    else:
                        break

                elif status == DONE:
                    json = self.reward(mission['id'])
                    running = True
                    break
