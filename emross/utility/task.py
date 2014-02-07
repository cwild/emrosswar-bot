import math
import threading
import time

from emross.utility.base import EmrossBaseObject

class Task(EmrossBaseObject):
    """
    This is just an abstraction. Not for direct use.
    """
    INTERVAL = 60

    def __init__(self, *args, **kwargs):
        super(Task, self).__init__(*args, **kwargs)

        self.lock = threading.Lock()
        self._result = dict()
        self._last_cycle = 0
        self._next_run = 0
        self.setup()

    def run(self, cycle_start, stage, *args, **kwargs):
        """
        Run this task if the cycle_start time differs

        A result is returned for this task; either from the previous cycle
        or as the result of processing this cycle. Necessary incase a blocking
        task has fired previously and is not rescheduled to run yet.
        """
        with self.lock:
            if self._last_cycle == cycle_start or cycle_start > self._next_run:
                self._last_cycle = cycle_start
                self._result[stage] = self.process(*args, **kwargs)

                if self._next_run < cycle_start:
                    delay = self.calculate_delay()
                    self.sleep(delay)

        return self._result.get(stage, None)

    def calculate_delay(self):
        return self.INTERVAL

    def process(self, *args, **kwargs):
        pass

    def setup(self):
        pass

    def sleep(self, seconds=INTERVAL):
        self._next_run = time.time() + seconds


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


class CostCalculator(object):
    COST_MODIFIER = 0
    COSTS = {}

    @classmethod
    def cost(cls, tech, level=2, modifier=None):
        modifier = modifier or cls.COST_MODIFIER
        costs = {}

        try:
            base_cost = cls.COSTS[tech]
            for t in ['g', 'w', 'f', 'i']:
                c = base_cost[t] * (1 + modifier)**(level-1)
                costs[t] = int(math.ceil(c))
        except IndexError:
            pass

        return costs

class FilterableCityTask(Task):

    def cities(self, city_names=None, city_index=None, **kwargs):
        cities = self.bot.cities

        if self.bot.pvp:
            # There shall be only ONE!
            pass
        elif city_index is not None:
            try:
                low, high = city_index
                cities = cities[low:high]
            except TypeError:
                cities = [cities[city_index]]
        elif city_names:
            cities = [city for city in cities if city.name in city_names]
        return cities
