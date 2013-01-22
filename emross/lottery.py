from emross.utility.task import Task

import logging
logger = logging.getLogger(__name__)


class AutoLottery(Task):
    INTERVAL = 5
    LOTTERY_API = 'game/lottery_api.php'

    def process(self):
        if self.bot.userinfo and self.bot.userinfo['lottery']:

            while True:
                logger.info('List the lottery items')
                json = self._wheel('list')

                logger.info('Spin the wheel')
                json = self._wheel('rotate')
                remain = int(json['ret']['remain'])

                if remain < 1:
                    break

                logger.info('Remaining wheel spins: %d' % remain)

            self.bot.userinfo['lottery'] = None
            self.sleep(3600)


    def _wheel(self, action):
        json = self.bot.api.call(self.LOTTERY_API, action=action)
        return json
