from copy import deepcopy
import logging

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

        self.log.info('Run Hero visit routine')
        json = self.bot.api.call(self.URL)
        if json['code'] != EmrossWar.SUCCESS:
            return True

        already_visited = self.split_heroes(json['ret']['visited_list'])
        can_visit_list = self.split_heroes(json['ret']['can_visit_list'])

        if already_visited:
            self.log.info('Heroes already visited: {0}'.format(', '.join([str(Hero(h)) for h in already_visited])))
        else:
            self.log.info('No heroes have been visited yet')
        self.log.info('Heroes available to visit: {0}'.format(', '.join([str(Hero(h)) for h in can_visit_list])))

        visited = self.calculate_components([(Hero(h).client['rank'], Hero(h).client['race']) for h in already_visited])

        cooldown = int(json['ret']['refresh_time'])

        for arg in args:
            target = self.calculate_components(arg)

            if self.compare_heroes(visited, target):
                self.log.info('Looks like we have a match!')
                price = self.reward_conversion(target)
                if price:
                    self.log.info('Turn in our reward')
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
                heroes.append({'gid':gid, 'rank':rank, 'face':face})
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

        self.log.debug('Current heroes {0}'.format(current))
        self.log.debug('Target heroes {0}'.format(target))

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
            self.log.debug('{0} unaccounted for in current target'.format(remain))

            return remain == 0

        except KeyError as e:
            self.log.exception(e)
            return False

    def visit_hero(self, position=0):
        """
        Position is between 1 and 5
        """
        if position not in range(1, 6):
            city = self.bot.cities[0]
            return self.bot.api.call(self.URL, action='visit', visit_gen=position, city=city.id)
        else:
            self.log.debug('Invalid position: {0}'.format(position))
            return False

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
            self.log.warning('Unable to calculate hero price')
            return

        price = '%d_%s' % (count, combo)
        self.log.debug('Calculated price: {0}'.format(price))

        return price

    def _calc_same(self, hero_selection, num=3):
        return num in set([sum(rank.values()) \
            for rank in hero_selection.itervalues()])



if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    from bot import bot
    bot.update()
    visit = HeroVisit(bot)

    current = {Hero.QUEEN: {2: 1}, Hero.JACK: {2: 3}}
    # any 1 Queen, any 3 Jack
    target = {Hero.QUEEN: {'*': 1}, Hero.JACK: {'*': 3}}
    if visit.compare_heroes(current, target):
        visit.reward_conversion(target)


    current = {Hero.QUEEN: {2: 1, 3: 1}}
    # any 2 Queens
    target = {Hero.QUEEN: {'*': 2}}
    if visit.compare_heroes(current, target):
        visit.reward_conversion(target)
