import time

from emross.api import EmrossWar
from emross.utility.base import EmrossBaseObject
from emross.utility.events import Event
from emross.utility.task import TaskType
from lib.cacheable import CacheableData

class CountdownManager(EmrossBaseObject, CacheableData):
    GET_COUNTDOWN_INFO = 'game/get_cdinfo_api.php'
    GET_COUNTDOWN_PRICE = 'game/api_getcdprice.php'
    COUNTDOWN_PRICE_INTERVAL = 300
    COUNTDOWN_ACTIONS = {
        TaskType.BUILDING: 'build',
        TaskType.RESEARCH: 'study'
    }

    def __init__(self, bot, city):
        super(CountdownManager, self).__init__(bot, time_to_live=60)
        self.city = city
        self.last_cdprice_check = 0
        self.bot.events.subscribe('city.countdown.reload', self._reload)

    def _reload(self, event, city_id):
        if city_id == self.city.id:
            self.expire()

    def should_update(self):
        return self.is_tainted(self._data['cdlist'])

    def update(self):
        json = self.get_countdown_info()
        d = json['ret']['cdlist']

        try:
            existing = self._data['cdlist']
            previous = set(t['id'] for t in existing)
            current = set(t['id'] for t in d)

            for _id in previous-current:
                try:
                    self.log.debug(_id)
                    self.bot.events.notify(
                        Event('countdown.task.expired', city=self.city),
                        [t for t in existing if t['id'] == _id][0]
                    )
                except IndexError as e:
                    self.log.exception(e)
        except KeyError:
            pass

        d[:] = self._normalise(d)
        return json

    def _normalise(self, tasks):
        """
        Convert the secs into timestamps so we actually know when they
        are expired
        """
        for task in tasks:
            task['secs'] += time.time()
        return tasks

    def is_tainted(self, tasks):
        """
        Check if any of the tasks should now be completed.
        Fire an event for each expired task
        """
        tainted = False
        for task in tasks:
            if task['secs'] < time.time():
                tainted = True
                self.log.debug('Tainted task list (time={0}): {1}'.format(time.time(), task))
                event = Event('countdown.task.expired', city=self.city)
                self.bot.events.notify(event, task)

        return tainted

    def get_countdown_info(self):
        """
        Get info about countdown tasks for a city
        {"code":0,"ret":{"cdlist":[{"id":12345678,"cdtype":1,"target":5,"owner":0,"secs":130}],"grade":36,"money":2}}
        """
        return self.bot.api.call(self.GET_COUNTDOWN_INFO, city=self.city.id)

    def get_tasks(self, task_type=None):
        return [task for task in self.data['cdlist'] if task_type in (None, task['cdtype'])]

    def add_tasks(self, tasks):
        tasks = self._normalise(tasks)
        self._data.setdefault('cdlist', []).extend(tasks)

        """
        The Emross client does this when one of the events has completed.
        This is important as you cannot initiate any task if you have not synced with the server.
        """
        self.update()
        self.city.expire()

    def remove_task(self, task):
        try:
            self._data['cdlist'].remove(task)
        except ValueError as e:
            self.log.error(e)

    def use_items_for_task(self, task, items):
        if (time.time() - self.last_cdprice_check) < self.COUNTDOWN_PRICE_INTERVAL:
            return
        else:
            self.last_cdprice_check = time.time()

        self.log.info('Decrease task time using items')
        self.log.debug(task)

        sorted_items = items[:]
        sorted_items.sort(key=lambda item: item[1], reverse=True)
        self.log.debug(sorted_items)

        remaining = int(task['secs'] - time.time())

        self.log.debug('Remaining time for task is {0} seconds'.format(remaining))

        json = self.bot.item_manager.find([item_id for item_id, time_offset in items])

        if json['code'] == EmrossWar.SUCCESS:
            available = dict([(item['sid'], item) for item in json['ret']['item']])

            for item_id, time_offset in sorted_items:
                try:
                    action = self.COUNTDOWN_ACTIONS[task['cdtype']]

                    while remaining > time_offset and available[item_id]['num'] > 0:
                        json = self._reduce_with_item(task['id'], action, item_id)

                        if json['code'] != EmrossWar.SUCCESS:
                            break

                        remaining = json['ret']['secs']
                        available[item_id]['num'] -= 1
                except KeyError:
                    pass

            self.log.info('Finished using items: {0} seconds remain'.format(remaining))
            task['secs'] = remaining + time.time()

    def _reduce_with_item(self, tid, action, item_id):
        json = self.bot.api.call(self.GET_COUNTDOWN_INFO, city=self.city.id, tid=tid, action=action, iid=item_id)

        if json['code'] == EmrossWar.SUCCESS:
            self.bot.inventory.adjust_item_stock(item_id)

        return json

    def use_gems_for_task(self, task, gems=0, **kwargs):
        """
        Try to complete a task with the specified number of gems
        """

        if not gems:
            # No need to do any work here
            return

        self.log.info('Attempt to gem the specified task')
        self.log.debug(task)

        available_gems = self.bot.userinfo.get('money', 0)

        if max(0, available_gems) < gems:
            return

        remaining = int(task['secs'] - time.time())
        json = self.bot.api.call(self.GET_COUNTDOWN_PRICE, type=task['cdtype'], secs=remaining)

        cost = int(json['ret'].get('price'))

        if cost > gems:
            self.log.info('Too expensive for specified number of gems')
        elif cost == gems:
            self.log.info('Use {0} gems to complete task {1}'.format(gems, task))
            json = self.bot.api.call(self.GET_COUNTDOWN_INFO, city=self.city.id, tid=task['id'], action='build2')

            if json['code'] == EmrossWar.SUCCESS:
                self.bot.userinfo['money'] = json['ret'].get('money', available_gems-cost)
                self.remove_task(task)
                self.city.expire()
