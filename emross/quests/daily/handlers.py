try:
    from collections import OrderedDict
except ImportError:
    from lib.ordered_dict import OrderedDict


from emross.alliance.donator import Donator
from emross.utility.base import EmrossBaseObject


MISSION_HANDLERS = OrderedDict()

class Mission(object):
    def __init__(self, data):
        self.data = data

class MissionHandler(EmrossBaseObject):
    def process(self, mission, *args, **kwargs):
        self.log.debug((mission, args, kwargs))
        return False


class HallDonationHandler(MissionHandler):
    def process(self, mission, amount, *args, **kwargs):
        self.log.debug('Required donation amount is {0}'.format(amount))

        if self.bot.alliance.in_ally:
            return self.bot.builder.task(Donator).donate_to_hall(gold=amount)

MISSION_HANDLERS['164'] = (HallDonationHandler, (10000,), {})
MISSION_HANDLERS['165'] = (HallDonationHandler, (20000,), {})
MISSION_HANDLERS['166'] = (HallDonationHandler, (30000,), {})
MISSION_HANDLERS['167'] = (HallDonationHandler, (40000,), {})
MISSION_HANDLERS['168'] = (HallDonationHandler, (50000,), {})
MISSION_HANDLERS['169'] = (HallDonationHandler, (60000,), {})
MISSION_HANDLERS['170'] = (HallDonationHandler, (70000,), {})
MISSION_HANDLERS['171'] = (HallDonationHandler, (80000,), {})
MISSION_HANDLERS['172'] = (HallDonationHandler, (100000,), {})
