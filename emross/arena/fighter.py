from collections import defaultdict
from copy import deepcopy

from emross.alliance import AllyTech
from emross.api import EmrossWar
from emross.arena import CONSCRIPT_URL
from emross.arena.hero import Hero
from emross.utility.base import EmrossBaseObject
from emross.utility.task import FilterableCityTask

VIGOR = EmrossWar.TRANSLATE['f_city_hero'].get('16', 'Vigor:')[:-1]


class OpponentFinder(EmrossBaseObject):
    def __init__(self, bot):
        super(OpponentFinder, self).__init__(bot)
        self.opponents = defaultdict(dict)
        self.opponent_victors = set()

    def find_arena_opponent(self, hero, level=1, searches=3):
        for i in range(searches):
            if len(self.opponents.get(level+1, {}).keys()) < 1:
                heroes = self.get_arena_opponents(level)

                try:
                    for opponent in heroes:
                        lvl = int(opponent[Hero.LEVEL])
                        oppid = opponent['id']
                        if oppid in self.opponent_victors:
                            self.log.debug('Skip {} as it has beaten us already'.format(opponent))
                            continue
                        self.opponents[lvl][oppid] = opponent
                except KeyError:
                    pass


        last_resort = []
        opponent = None
        for lvl in range(level+1, level-2, -1):
            if lvl in self.opponents:
                try:
                    last_resort.append(self.opponents[lvl].values()[0])
                except IndexError:
                    continue
                opponent = self.select_preferred_opponent(hero, self.opponents[lvl])

                if opponent:
                    self.log.debug('Found an opponent at level {0}, stop search'.format(lvl))
                    break

        opp = opponent or last_resort[0]
        self.log.info('Our {0} will fight an opposing {1}'.format(hero, Hero(opp)))
        return opp

    def get_arena_opponents(self, level=1):
        """
        game/gen_conscribe_api.php lv=17

        {"code":0,"ret":{"hero":[
            {"id":654321,"gid":107,"g":17,"w":0,"uid":123456,"u":"PLAYER",
                "r":2,"gname":"ALLIANCE NAME","gflag":10,"reborn":0},
            ]}
        }
        """

        try:
            json = self.bot.api.call(CONSCRIPT_URL, lv=level)
            return json['ret']['hero']
        except Exception:
            self.log.error('Problem retrieving opponents from the arena')
            return []


    def select_preferred_opponent(self, hero, opponents):
        def rank(gid):
            return EmrossWar.HERO[str(gid)]['rank']

        opp = None
        for oppid, opponent in opponents.iteritems():
            # <= because hero ranks are ordered strongest first (a-e)
            if hero.client['rank'] <= rank(opponent['gid']):
                if opp is None or \
                    (rank(opponent['gid']), opponent[Hero.WINS]) >= (rank(opp['gid']), opp[Hero.WINS]):
                    # Chosen the lower ranked hero or the hero with lowest win-streak
                    opp = opponent

        return opp

    def remove_opponent(self, opponent):
        """
        If an opponent beats us, we don't want to face it again this round
        """
        lvl = int(opponent[Hero.LEVEL])
        oppid = opponent['id']
        del self.opponents[lvl][oppid]
        self.opponent_victors.add(oppid)
        self.log.info(u'Removed hero "{0}" from "{1}"'.format(Hero(opponent), opponent['u']))

class ArenaFighter(FilterableCityTask):
    INTERVAL = 1800
    VIGOR_BASE = 10
    LOSS = -1
    DRAW = 0
    WIN = 1

    def attack(self, hero, target):
        """
        {"code":0,"ret":{"exp":985,"win":-3}}

        win>0, draw=0, loss<0
        """
        return self.bot.api.call(CONSCRIPT_URL, gid=hero, tgid=target)


    def process(self, below=1, loss_limit=1, searches=3, *args, **kwargs):
        """
        below - how many vigor below max should we stay?
        loss_limit - how many concurrent defeats before deciding target is too strong?
        searches - how many times should we try looking for heroes at a given level?
        """

        max_vigor = self.VIGOR_BASE + (2 * self.bot.alliance.tech(AllyTech.INCENTIVE))
        self.log.info('Max {0} is {1}'.format(VIGOR, max_vigor))
        below = min(below, max_vigor)

        opponents = OpponentFinder(self.bot)

        cities = self.cities(**kwargs)
        for city in cities:
            for hero in city.hero_manager.heroes.itervalues():
                remaining = hero.data.get(Hero.VIGOR, 0)
                self.log.info('{0} has {amt} {vigor}. Current streak: {streak}, Total W/L: {win}/{loss}'.format(\
                    hero,
                    amt=remaining,
                    vigor=VIGOR,
                    streak=hero.data.get(Hero.WINS, 0),
                    win=hero.data.get(Hero.TOTAL_WINS, 0),
                    loss=hero.data.get(Hero.TOTAL_LOSSES, 0)
                    )
                )

                """
                Iterate the appropriate number of times to reduce remaining
                vigor to maximum vigor less the specified amount below
                """
                tainted = False
                losses = 0
                for _ in range(remaining + below - max_vigor):
                    level = hero.data.get(Hero.LEVEL)
                    opponent = opponents.find_arena_opponent(hero, level, searches)

                    json = self.attack(hero.data['id'], opponent['id'])
                    if json['code'] != EmrossWar.SUCCESS:
                        break

                    hero.data[Hero.EXPERIENCE] += json['ret']['exp']
                    if json['ret']['win'] <= self.LOSS:
                        losses += 1

                        if losses == loss_limit:
                            self.log.info('Loss limit reached, stopping fighting with {0}'.format(hero))
                            opponents.remove_opponent(opponent)
                            break
                    elif losses > 0:
                        losses -= 1

                    if hero.data.get(Hero.EXPERIENCE) > hero.data.get(Hero.TARGET_EXPERIENCE):
                        tainted = True
                        break


                if tainted:
                    city.hero_manager.expire()
                    self.sleep(5)
