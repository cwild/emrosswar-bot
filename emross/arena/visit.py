from copy import deepcopy
import logging
logger = logging.getLogger(__name__)

from emross.api import EmrossWar
from emross.utility.task import Task
from hero import Hero

class HeroVisit(Task):
    """
    Implementation of the Hero "Visit"/poker game in the arena.
    """

    INTERVAL = 30
    URL = 'game/gen_visit_api.php'
    UNMET_CURRENCY_CONDITIONS = 1610

    def process(self, *args, **kwargs):

        logger.info('Run Hero visit routine')
        json = self.bot.api.call(self.URL)
        if json['code'] != EmrossWar.SUCCESS:
            return True

        already_visited = self.split_heroes(json['ret']['visited_list'])
        can_visit_list = self.split_heroes(json['ret']['can_visit_list'])

        logger.info('Heroes already visited: %s' % ', '.join([str(Hero(h)) for h in already_visited]))
        logger.info('Heroes available to visit: %s' % ', '.join([str(Hero(h)) for h in can_visit_list]))

        visited = self.calculate_components([(h['rank'], h['race']) for h in already_visited])

        cooldown = int(json['ret']['refresh_time'])

        for arg in args:
            target = self.calculate_components(arg)

            if self.compare_heroes(visited, target):
                logger.info('Looks like we have a match!')
                price = self.reward_conversion(target)
                if price:
                    logger.info('Turn in our reward')
                    self.exchange_heroes(price)
                break


        self.sleep(cooldown)

    def split_heroes(self, data):
        """
        Break the encoded string up to extract the hero id, rank and card face
        """
        heroes = []
        try:
            for chunk in data.split(','):
                # HeroID, 10/J/Q/K/A, face of card
                gid, rank, face = chunk.split('|')
                heroes.append(EmrossWar.HERO[str(gid)])
        except ValueError:
            pass
        return heroes

    def calculate_components(self, parts):
        """
        Create a dict of this selection of heroes. Each hero "rank" has a dict
        of the faces it contains.
        """
        target = {}
        for part in parts:
            rank = part[0]

            try:
                face = part[1]
            except IndexError:
                face = '*'

            try:
                target[rank][face] += 1
            except KeyError:
                if rank not in target:
                    target[rank] = {}
                target[rank][face] = 1

        return target

    def compare_heroes(self, current, target):

        # Early optimisation
        if current == target:
            return True

        logger.debug('Current heroes %s' % current)
        logger.debug('Target heroes %s' % target)

        # Don't modify the originals
        current = deepcopy(current)
        target = deepcopy(target)

        try:
            for rank, _sub in current.iteritems():
                """
                The target does not contain a card present in the visited list
                eg. we have current [(ACE, HEARTS)] and target is [(QUEEN,), (QUEEN,)]
                """
                if rank not in target:
                    return False

                for face, count in _sub.iteritems():
                    for _ in range(count):
                        if target[rank].get(face, 0) > 0:
                            target[rank][face] -= 1

                        elif target[rank].get('*', 0) > 0:
                            target[rank]['*'] -= 1


            remain = sum([sum(v.values()) for k, v in target.iteritems()])
            logger.debug('%d unaccounted for in current target' % remain)

            return remain == 0

        except KeyError as e:
            logger.exception(e)
            return False

    def visit_hero(self, position=0):
        """
        Position is between 1 and 5
        """
        if position > 0:
            city = self.bot.cities[0]
            return self.bot.api.call(self.URL, action='visit', visit_gen=position, city=city.id)
        else:
            logger.debug('Invalid position: %d' % position)

    def exchange_heroes(self, price):
        """
        Collect the "reward" for the given price
        """
        return self.bot.api.call(self.URL, action='getprice', price_type=price)

    def clear_heroes(self):
        """
        Clear our current hand
        """
        return self.bot.api.call(self.URL, action='clear')

    def reward_conversion(self, hero_selection):
        """
        Convert the chosen heroes into the correct partcode

        2_c - Ladies
        3_b_c_d - J,Q,K
        3_same - Three of a kind
        4_same - Four of a kind
        4_double - Two pairs
        5_three - Full house
        5_same - Five of a kind
        5_different - Straight
        5_all_same - Royal Flush
        """
        count = sum([sum(rank.values()) for rank in hero_selection.itervalues()])
        combo = None

        if count == 2:
            # Only queens currently
            combo = Hero.QUEEN

        elif count == 3:
            if self._calc_same(hero_selection, 3):
                combo = 'same'
            else:
                combo = '_'.join(sorted([k for k in hero_selection.iterkeys()]))

        elif count == 4:
            pairs = [rank for rank, sub in hero_selection.iteritems() if sum(sub.values()) >= 2]
            if len(pairs) == 2:
                combo = 'double'
            elif self._calc_same(hero_selection, 4):
                combo = 'same'

        elif count == 5:
            if self._calc_same(hero_selection, 5):
                combo = 'same'

            elif len(hero_selection.keys()) == 5:
                faces = set([face for k, v in hero_selection.iteritems() \
                            for face in v.iterkeys()])
                if len(faces) == 1:
                    combo = 'all_same'
                else:
                    combo = 'different'

            elif len(hero_selection.keys()) == 2:
                cards = set([max(face.values()) for rank, face in \
                    hero_selection.iteritems()])

                if set([3,2]) == cards:
                    combo = 'three'


        if not combo:
            logger.warning('Unable to calculate hero price')
            return

        price = '%d_%s' % (count, combo)
        logger.debug('Calculated price: %s' % price)

        return price

    def _calc_same(self, hero_selection, num=3):
        return num in set([sum(rank.values()) \
            for rank in hero_selection.itervalues()])



if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    visit = HeroVisit(None)

    # 1 specific Queen, 1 specific Jack
    heroes = visit.split_heroes('172|d|1,68|c|4')
    current = visit.calculate_components( [(h['rank'], h['race']) for h in heroes] )

    visit.compare_heroes(current, visit.calculate_components( [(h['rank'], h['race']) for h in heroes] ))

    # any 1 Queen, any 1 Jack
    target = {Hero.QUEEN: {'*': 1}, Hero.JACK: {'*': 1}}
    visit.compare_heroes(current, target)

    # any 1 Queen, any 3 Jack
    target = {'c': {'*': 1}, 'd': {'*': 3}}
    #logging.info('Should be: FALSE')
    visit.compare_heroes(current, target)


    current = {'c': {2: 1}, 'd': {2: 3}}
    # any 1 Queen, any 1 Jack
    target = {Hero.QUEEN: {'*': 1}, Hero.JACK: {'*': 3}}
    if visit.compare_heroes(current, target):
        visit.reward_conversion(target)


    current = {Hero.QUEEN: {2: 1, 3: 1}}
    # any 2 Queens
    target = {Hero.QUEEN: {'*': 2}}
    if visit.compare_heroes(current, target):
        visit.reward_conversion(target)


    visit.reward_conversion({Hero.QUEEN: {2: 2}})

    logger.info('J,Q,K (3_b_c_d)')
    visit.reward_conversion({
        Hero.JACK: {'*': 1},
        Hero.QUEEN: {'*': 1},
        Hero.KING: {'*': 1}
    })

    logger.info('3 of a kind (3_same)')
    visit.reward_conversion({Hero.TEN: {'*': 3}})
    visit.reward_conversion({Hero.JACK: {'*': 3}})
    visit.reward_conversion({Hero.QUEEN: {'*': 3}})
    visit.reward_conversion({Hero.KING: {'*': 3}})
    visit.reward_conversion({Hero.ACE: {'*': 3}})

    logger.info('4 of a kind')
    visit.reward_conversion({Hero.TEN: {'*': 4}})
    visit.reward_conversion({Hero.JACK: {'*': 4}})
    visit.reward_conversion({Hero.QUEEN: {'*': 4}})
    visit.reward_conversion({Hero.KING: {'*': 4}})
    visit.reward_conversion({Hero.ACE: {'*': 4}})

    logger.info('2 pairs')
    visit.reward_conversion({Hero.JACK: {'*': 2}, Hero.TEN: {1: 2}})
    visit.reward_conversion({Hero.QUEEN: {'*': 2}, Hero.JACK: {1: 2}})
    visit.reward_conversion({Hero.KING: {'*': 2}, Hero.QUEEN: {1: 2}})
    visit.reward_conversion({Hero.ACE: {'*': 2}, Hero.KING: {1: 2}})

    logger.info('5 of a kind')
    visit.reward_conversion({Hero.TEN: {'*': 5}})
    visit.reward_conversion({Hero.JACK: {'*': 5}})
    visit.reward_conversion({Hero.QUEEN: {'*': 5}})
    visit.reward_conversion({Hero.KING: {'*': 5}})
    visit.reward_conversion({Hero.ACE: {'*': 5}})

    logger.info('Straight')
    visit.reward_conversion({
        Hero.TEN: {Hero.HEARTS: 1},
        Hero.JACK: {Hero.CLUBS: 1},
        Hero.QUEEN: {Hero.SPADES: 1},
        Hero.KING: {Hero.DIAMONDS: 1},
        Hero.ACE: {Hero.HEARTS: 1}
    })

    logger.info('Royal flush')
    visit.reward_conversion({
        Hero.TEN: {Hero.HEARTS: 1},
        Hero.JACK: {Hero.HEARTS: 1},
        Hero.QUEEN: {Hero.HEARTS: 1},
        Hero.KING: {Hero.HEARTS: 1},
        Hero.ACE: {Hero.HEARTS: 1}
    })

    logger.info('Full house (3 of same face) + pair')
    visit.reward_conversion({
        Hero.ACE: {Hero.DIAMONDS: 3},
        Hero.JACK: {Hero.CLUBS: 2}
    })
