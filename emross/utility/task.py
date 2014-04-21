import math
import threading
import time

from emross.utility.base import EmrossBaseObject

class Task(EmrossBaseObject):
    """
    This is just an abstraction. Not for direct use.
    """
    INTERVAL = 60

    """
    If ENFORCED_INTERVAL is set then we can search the bot.session for this value
    and only run if the INTERVAL has passed
    """
    ENFORCED_INTERVAL = False

    def __init__(self, *args, **kwargs):
        super(Task, self).__init__(*args, **kwargs)

        self.lock = threading.Lock()
        self._result = dict()
        self._last_cycle = 0
        self._next_run = 0
        self.setup()

    def finish_cycle(self):
        self._next_run = self.last_cycle
        self.last_cycle = 0.1
        self.log.debug('Do not run any further "{0}" tasks on the current build cycle'.format(self.__class__.__name__))

    @property
    def last_cycle(self):
        if self._last_cycle == 0 and self.ENFORCED_INTERVAL:
            self._last_cycle = getattr(self.bot.session, 'last_cycle_{0}'.format(self.__class__.__name__), 0)

        return self._last_cycle

    @last_cycle.setter
    def last_cycle(self, value):
        self._last_cycle = value

        if self.ENFORCED_INTERVAL:
            setattr(self.bot.session, 'last_cycle_{0}'.format(self.__class__.__name__), value)

    def run(self, cycle_start, stage, *args, **kwargs):
        """
        Run this task if the cycle_start time differs

        A result is returned for this task; either from the previous cycle
        or as the result of processing this cycle. Necessary incase a blocking
        task has fired previously and is not rescheduled to run yet.
        """
        with self.lock:
            if self.can_run_process(cycle_start):
                self.last_cycle = cycle_start

                self._result[stage] = self.process(*args, **kwargs)

                if self._next_run < cycle_start:
                    delay = self.calculate_delay()
                    self.sleep(delay)

        return self._result.get(stage, None)

    def can_run_process(self, cycle_start):
        if self.ENFORCED_INTERVAL and self.last_cycle + self.INTERVAL > cycle_start:
            # The enforced interval must pass first
            return False

        if self.last_cycle == cycle_start or cycle_start > self._next_run:
            return True

        return False

    def calculate_delay(self):
        return self.INTERVAL

    def process(self, *args, **kwargs):
        pass

    def reschedule(self, delay=-1):
        self._next_run = time.time() + delay

    def setup(self):
        pass

    def sleep(self, seconds=INTERVAL):
        self.reschedule(seconds or self.INTERVAL)


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
