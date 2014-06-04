"""
Automatically defend our cities against incoming attacks.
"""
import logging
import threading
import time

from emross.military.barracks import Barracks
from emross.utility.controllable import Controllable
from emross.utility.task import FilterableCityTask, TaskType

logger = logging.getLogger(__name__)

class Aggressor(object):
    """
    Describe a type of army and determine if we should defend against it
    """
    DEFEND = True
    PERMIT_UNKNOWN = False

    def __init__(self,
        army={},
        minimum_defensive_units={},
        defend=DEFEND,
        permit_unknown=PERMIT_UNKNOWN,
        maximum_troops=None,
        *args, **kwargs):

        self.army = army
        self.minimum_defensive_units = minimum_defensive_units
        self.defend = defend
        self.permit_unknown = permit_unknown
        self.maximum_troops = maximum_troops

    def defendable(self, incoming, available=[], maximum_troops=None, \
        minimum_defensive_units={}):
        """
        Should we try to defend against this attack?
        """

        # Has an overall maximum been specified?
        maximum = self.maximum_troops or maximum_troops

        # If the incoming army exceeds this then do not defend
        if maximum and sum(incoming.values()) > maximum:
            logger.debug('Incoming troops exceed the maximum of {0}'.format(maximum))
            return False

        applicable_units = 0

        for troop, quantities in self.army.iteritems():
            incoming_qty = incoming.get(troop, 0)

            if not incoming_qty and not self.permit_unknown:
                logger.debug('Only specified troop types are permitted')
                return not self.defend

            min_troops, max_troops = quantities

            if min_troops <= incoming_qty <= max_troops:
                applicable_units += 1


        unrecognised = set(incoming.keys()) - set(self.army.keys())
        if not self.permit_unknown and unrecognised:
            logger.debug('Unrecognised incoming units: {0}'.format(unrecognised))
            return False

        # We have found each of the types of troop we are looking for
        if applicable_units == len(self.army.keys()):

            # Create a dict of soldiers and quantities
            soldiers = dict([(s[0], s[1]) for s in available])

            # Use the most specific setting
            mdu = self.minimum_defensive_units or minimum_defensive_units

            for troop, qty in mdu.iteritems():
                # Not enough of our specified defensive troops to defend this attack
                if soldiers.get(troop) < qty:
                    return False

            return self.defend

        logger.debug('Units: applicable {0}, found {1}'.format(applicable_units, len(self.army.keys())))
        return not self.defend

class AutoDefense(FilterableCityTask, Controllable):
    BLOCK = False
    CLOSE_AFTER = 1
    COMMAND = 'defense'
    INTERVAL = 60
    MAXIMUM_TROOPS = None
    OPEN_BEFORE = 3
    PREPARATION_TIME = 30
    PUSHOVER = True
    REPORT = True

    def setup(self):
        self.bot.events.subscribe('barracks.war.info', self.monitor)
        self.bot.events.subscribe('city.countdown.reload', self.monitor)
        self.known_attacks = getattr(self.bot.session, 'known_attacks', set())
        self.defense_workers = set()

    def monitor(self, event, *args, **kwargs):
        self.reschedule()

    def process(self,
        armies=[],
        minimum_defensive_units={},
        interval=None,
        maximum_troops=None,
        open_before=None,
        close_after=None,
        preparation_time=None,
        strategy=None,
        block=None,
        report=None,
        pushover=None,
        *args, **kwargs):

        # Allow these to all be overridden at class level
        interval = interval or self.INTERVAL
        maximum_troops = maximum_troops or self.MAXIMUM_TROOPS
        open_before = open_before or self.OPEN_BEFORE
        close_after = close_after or self.CLOSE_AFTER
        preparation_time = preparation_time or self.PREPARATION_TIME
        strategy = strategy or Barracks.DO_NOT_ENGAGE
        block = self.BLOCK if block is None else block
        report = self.REPORT if report is None else report
        pushover = self.PUSHOVER if pushover is None else pushover

        """
        {'code': 0, 'ret': [
            [
                [
                    123123, #id
                    6, #cooldowntype
                    0, #actiontype
                    478, #seconds
                    '112/220', #destination
                    [2, 11, 17], # unit type
                    [1, 1, 1], # unit quantity
                    103, # hero gid
                    u'ATTACKER', # attacking player name
                    '123/123' # attack origin co-ords
                ]
            ],

            20] # defense facility
        }
        """
        cities = self.cities(**kwargs)
        defending_cities = dict()
        known_attacks = set()
        all_attacks = []

        for city in cities:
            # First, ensure our strategy matches what has been configured
            city.barracks.defense_strategy(strategy, sleep=False)

            defending_cities['{0.x}/{0.y}'.format(city)] = city

            # What's currently happening in the war room?
            war_info = city.barracks.war_room(sleep=False)

            attacks, defense_facility = war_info['ret'][0:2]

            for attack in attacks:
                if attack[1] != TaskType.INCOMING or \
                    attack[2] not in (Barracks.LOOT, Barracks.CONQUER):

                    # This is not an incoming player attack
                    continue

                if attack[0] not in known_attacks:
                    attack[3] += time.time()
                    all_attacks.append(attack)

                known_attacks.add(attack[0])


        # Now that we know about all of our incoming attacks, sort on the closest one..
        all_attacks.sort(key=lambda att: att[3])
        earliest_defense_time_per_city = {}
        defendable_attacks = []

        for attack in all_attacks:
            city = defending_cities.get(attack[4])

            # We are not defending the city at these co-ords
            if not city:
                continue

            troops = dict(zip(attack[5], attack[6]))
            self.log.debug(troops)

            should_defend = False
            for aggressor in armies:
                try:
                    if aggressor.defendable(troops, city.barracks.soldiers, maximum_troops, minimum_defensive_units):
                        should_defend = True
                        break
                except Exception as e:
                    self.log.exception(e)
                    continue

            if not should_defend:
                city.barracks.defense_strategy(Barracks.DO_NOT_ENGAGE, sleep=False)
            else:
                defendable_attacks.append((city,attack))

                if earliest_defense_time_per_city.get(city) < attack[3]:
                    earliest_defense_time_per_city[city] = attack[3]

            try:
                hero = attack[7]
                attacker = attack[8]
                attacker_coords = attack[9]
            except IndexError:
                pass


        self.log.debug(all_attacks)

        delays = [interval+time.time()]
        for city, attack in defendable_attacks:
            impact_time = attack[3]
            impact_seconds = int(impact_time - time.time())

            if False and impact_seconds > preparation_time:
                # Set this up to use a relative time when issuing the sleep
                delays.append(impact_time - preparation_time)
            else:
                # We don't want to open while there is another undefendable attack inbound
                wait_periods = [0, impact_seconds - open_before]

                # Don't sleep beyond our own impact_time
                if earliest_defense_time_per_city[city] != impact_time:
                    wait_periods.append(earliest_defense_time_per_city[city] - time.time())


                def _worker(workers, wait_periods, city, attack):
                    try:
                        self.log.debug(u'Begin handling {0}, start sleep'.format(attack))
                        time.sleep(max(wait_periods))

                        city.barracks.defense_strategy(Barracks.PROTECT_CASTLE, sleep=False)
                        self.log.debug(u'Engaged for attack, restore defense strategy after {0} seconds'.format(close_after))
                        time.sleep(max(0, impact_time-time.time() + close_after))

                        # Restore to the previous strategy
                        city.barracks.defense_strategy(strategy, sleep=False)

                        # Update the soldier listing.. we may be wounded after that attack!
                        city.barracks.expire()
                    finally:
                        # Job done!
                        workers.remove(attack[0])

                if attack[0] in self.defense_workers:
                    continue

                # Only a single handler should deal with this
                self.defense_workers.add(attack[0])

                if block:
                    _worker(self.defense_workers, wait_periods, city, attack)
                else:
                    t = threading.Thread(target=_worker, \
                        args=(self.defense_workers, wait_periods, city, attack))
                    t.daemon = True
                    t.start()

        # This is relative to any other defending we may have already done
        self.sleep(min(delays) - time.time())

        if report and all_attacks:
            new_attacks = [att for att in attacks if att[0] not in self.known_attacks]
            attackers = []
            for att in all_attacks:
                try:
                    attackers.append(att[8])
                except IndexError:
                    attackers.append('?')

            msg = u'Incoming loots: {0} ({1} new)! Attackers: {2}'.format(\
                    len(all_attacks),
                    len(new_attacks),
                    u', '.join(attackers)
            )

            self.log.info(msg)

            if new_attacks and pushover:
                self.bot.pushover.send_message(u'{0} has {1}'.format(\
                    self.bot.userinfo.get('nick'), msg
                ))

        self.bot.session.known_attacks = self.known_attacks = known_attacks
