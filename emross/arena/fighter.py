from collections import defaultdict
from copy import deepcopy

from emross.alliance import AllyTech
from emross.api import EmrossWar
from emross.chat import Channel
from emross.arena import CONSCRIPT_URL
from emross.arena.hero import Hero
from emross.mail.mailer import Mailer
from emross.utility.base import EmrossBaseObject
from emross.utility.controllable import Controllable
from emross.utility.task import FilterableCityTask

VIGOR = EmrossWar.TRANSLATE['f_city_hero'].get('16', 'Vigor:')[:-1]


class OpponentFinder(EmrossBaseObject):
    def __init__(self, bot):
        super(OpponentFinder, self).__init__(bot)
        self.opponents = defaultdict(dict)
        self.opponent_victors = set()

    def find_opponents(self, level, searches=3, *args, **kwargs):
        searches = int(searches)
        opponents = defaultdict(dict)
        for _ in xrange(searches):
            heroes = self.get_arena_opponents(level)

            for opponent in heroes:
                lvl = int(opponent[Hero.LEVEL])
                oppid = opponent['id']
                opponents[lvl][oppid] = opponent

        return opponents

    def find_arena_opponent(self, hero, level=1, **kwargs):

        if len(self.opponents.get(level+1, {}).keys()) < 1:
            opponents = self.find_opponents(level, **kwargs)

            for lvl, opps in opponents.iteritems():
                for oppid, opp in opps.iteritems():
                    if oppid in self.opponent_victors:
                        self.log.debug('Skip {0} as it has beaten us already'.format(opp))
                        continue
                    self.opponents[lvl][oppid] = opp

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


class ArenaFighter(FilterableCityTask, Controllable):
    COMMAND = 'fighter'
    INTERVAL = 1800
    VIGOR_BASE = 10
    LOSS = -1
    DRAW = 0
    WIN = 1

    def action_attack(self, event, hero, target,
                    stoponlose=1, *args, **kwargs):
        """
        Specify a "hero" and a "target" for it to attack.
        """

        stoponlose = int(stoponlose)
        _hero = Hero.find(hero, *args, **kwargs)

        if not _hero:
            return

        hero_id = None
        for city in self.cities(**kwargs):
            try:
                for _id, h in city.hero_manager.heroes.iteritems():
                    if int(h.data.get('gid')) == _hero['hero_id']:
                        hero_id, hero = _id, h
                        break
                break
            except KeyError:
                pass

        if not hero_id:
            self.send_message('Could not find the specified hero', event=event)
            return

        self.chat.send_message('{0} has {1} {2} for fighting'.format(hero, \
            hero.data.get(Hero.VIGOR, 0), VIGOR), event=event)

        while hero.data.get(Hero.VIGOR, 0) > 0:
            json = self.attack(hero_id, int(target))
            if json['code'] != EmrossWar.SUCCESS:
                try:
                    msg = EmrossWar.LANG['ERROR']['SERVER'][str(json['code'])]
                except KeyError:
                    msg = 'Stopping after error {0} occurred!'.format(json['code'])
                self.chat.send_message(msg, event=event)
                break

            hero.data[Hero.VIGOR] -= 1
            hero.data[Hero.EXPERIENCE] += int(json['ret']['exp'])

            if hero.data.get(Hero.EXPERIENCE) > hero.data.get(Hero.TARGET_EXPERIENCE):
                city.hero_manager.expire()

            if json['ret']['win'] <= self.LOSS:
                if stoponlose:
                    self.chat.send_message('{0} retires after defeat'.format(hero), event=event)
                    break

    def action_search(self, event, level=None, exact=0, *args, **kwargs):
        """
        Find heroes of the given "level"
        """
        event.propagate = False
        exact = int(exact)
        try:
            level = int(level)

            if level < Hero.MIN_LEVEL or level > Hero.MAX_LEVEL:
                raise ValueError

        except (TypeError, ValueError):
            self.chat.send_message('You need to specify a hero "level" between {0} and {1}.'.format(\
                Hero.MIN_LEVEL, Hero.MAX_LEVEL),
                event=event
            )

        self.chat.send_message('I will have a look and send you a mail shortly', event=event)

        mailer = self.bot.builder.task(Mailer)
        title = 'As requested: Level {0} heroes'.format(level)

        opponents = OpponentFinder(self.bot).find_opponents(level, **kwargs)
        if not opponents:
            messages = ["Sorry, there don't appear to be any heroes around that level"]
        else:
            messages = ['Following your request, here are some of the heroes found in the arena:', '']

            for lvl in sorted(opponents.iterkeys(), reverse=True):
                if exact and lvl != level:
                    continue
                messages.append('LEVEL {0}'.format(lvl))
                messages.append('='*20)

                for opponent in opponents[lvl].itervalues():
                    messages.append(u'{0} ({1}). id={id}, wins={streak}'.format(
                        Hero(opponent), opponent['u'],
                        id=opponent['id'], streak=opponent[Hero.WINS]
                    ))

        mailer.send_mail(event.player_name, title, EmrossWar.safe_text('\n'.join(messages)))

    def attack(self, hero, target):
        """
        {"code":0,"ret":{"exp":985,"win":-3}}

        win>0, draw=0, loss<0
        """
        return self.bot.api.call(CONSCRIPT_URL, gid=hero, tgid=target)


    def process(self, below=1, loss_limit=1, *args, **kwargs):
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
                    opponent = opponents.find_arena_opponent(hero, level, **kwargs)

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
