from emross.utility.task import Task

class AutoLottery(Task):
    INTERVAL = 1800
    LOTTERY_API = 'game/lottery_api.php'

    def process(self):

        # Don't check bot.data as it expires - prevent surplus userinfo updates
        if not self.bot._data:
            self.sleep(15)

        elif self.bot._data.get('lottery'):

            while True:
                self.log.info('List the lottery items')
                json = self._wheel('list')

                self.log.info('Spin the wheel')
                json = self._wheel('rotate')
                remain = int(json['ret']['remain'])

                if remain < 1:
                    self.log.info('Out of spins')
                    break

                self.log.info('Remaining wheel spins: {0}'.format(remain))

            self.bot.userinfo['lottery'] = None
            self.sleep(3600)


    def _wheel(self, action):
        return self.bot.api.call(self.LOTTERY_API, action=action)
