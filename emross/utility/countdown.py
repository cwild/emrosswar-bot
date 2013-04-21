import logging
import time

logger = logging.getLogger(__name__)

class CountdownManager(object):
    GET_COUNTDOWN_INFO = 'game/get_cdinfo_api.php'

    def __init__(self, bot, city):
        self.bot = bot
        self.city = city
        self._data = None
        self.last_update = 0

    @property
    def data(self):
        if self._data is None or (time.time() - self.last_update) > 60 \
            or self.is_tainted(self._data['ret']['cdlist']):
            self.update()

        return self._data

    def update(self):
        self._data = self.get_countdown_info()
        self.last_update = time.time()
        d = self._data['ret']['cdlist']
        d[:] = self._normalise(d)

    def _normalise(self, tasks):
        """
        Convert the secs into timestamps so we actually know when they
        are expired
        """
        for task in tasks:
            task['secs'] += time.time()
        return tasks

    def is_tainted(self, tasks):
        tainted = len(tasks) != len([t for t in tasks if t['secs'] > time.time()])
        if tainted:
            logger.debug('Tainted task list (time=%f): %s' % (time.time(), tasks))
        return tainted

    def get_countdown_info(self):
        """
        Get info about countdown tasks for a city
        {"code":0,"ret":{"cdlist":[{"id":12345678,"cdtype":1,"target":5,"owner":0,"secs":130}],"grade":36,"money":2}}
        """
        return self.bot.api.call(self.GET_COUNTDOWN_INFO, city=self.city.id)

    def get_tasks(self, task_type=None):
        return [task for task in self.data['ret']['cdlist'] if task_type in (None, task['cdtype'])]

    def add_tasks(self, tasks):
        tasks = self._normalise(tasks)
        self._data['ret']['cdlist'].extend(tasks)

        """
        The Emross client does this when one of the events has completed.
        This is important as you cannot initiate any task if you have not synced with the server.
        """
        self.update()
        self.city.update()
