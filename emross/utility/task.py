import math
import time

class Task(object):
    """
    This is just an abstraction. Not for direct use.
    """

    def process(self, *args, **kwargs): pass


class TaskType:
    DEGRADE = 0
    BUILDING = 1
    RESEARCH = 2
    TRAIN = 3
    ACTION = 4
    RETURN = 5
    INCOMING = 6
    COLONY = 7
    PROTECT = 8


class CostCalculator:
    @classmethod
    def cost(cls, tech, level):
        costs = {}

        try:
            base_cost = cls.COSTS[tech]
            for t in ['g', 'w', 'f', 'i']:
                c = base_cost[t] * (1 + cls.COST_MODIFIER)**(level-1)
                costs[t] = int(math.ceil(c))
        except IndexError:
            pass

        return costs


class CountdownManager:
    GET_COUNTDOWN_INFO = 'game/get_cdinfo_api.php'

    def __init__(self, bot, city):
        self.bot = bot
        self.city = city
        self._data = None
        self.last_update = 0

    @property
    def data(self):
        if self._data is None or (time.time() - self.last_update) > 60:
            self.update()

        l = self._data['ret']['cdlist']
        l = [c for c in l if c['secs'] > time.time()]
        return self._data

    def update(self):
        self._data = self.get_countdown_info()
        self.last_update = time.time()

        for task in self._data['ret']['cdlist']:
            task['secs'] += time.time()

    def get_countdown_info(self):
        """
        Get info about countdown tasks for a city
        {"code":0,"ret":{"cdlist":[{"id":12345678,"cdtype":1,"target":5,"owner":0,"secs":130}],"grade":36,"money":2}}
        """
        return self.bot.api.call(self.GET_COUNTDOWN_INFO, city=self.city.id)

    def get_tasks(self, task_type=None):
        return [task for task in self.data['ret']['cdlist'] if task_type is None or task_type == task['cdtype']]

    def add_tasks(self, tasks):
        self.data['ret']['cdlist'].extend(tasks)
