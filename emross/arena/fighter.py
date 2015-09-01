from collections import defaultdict
from copy import deepcopy

from emross.alliance import AllyTech
from emross.api import EmrossWar
from emross.chat import Channel
from emross.arena import CONSCRIPT_URL
from emross.arena.hero import Hero
from emross.item import inventory, item
from emross.mail.mailer import Mailer
from emross.resources import Resource
from emross.utility.base import EmrossBaseObject
from emross.utility.controllable import Controllable
from emross.utility.task import FilterableCityTask

from lib import six

VIGOR = EmrossWar.TRANSLATE['f_city_hero'].get('16', 'Vigor:')[:-1]
USER_SPECIFIED = _('User Specified')

class TargetManager(dict):
    def __missing__(self, key):
        """
        `key` is the world name.
        So ['world'] should return a dictionary of hero levels
        """
        self[key] = value = defaultdict(list)
        return value

class OpponentFinder(EmrossBaseObject):
    def __init__(self, bot):
        super(OpponentFinder, self).__init__(bot)
        self.opponents = defaultdict(dict)
        self.opponent_victors = set()

    def find_opponents(self, level, searches=3, *args, **kwargs):
        opponents = defaultdict(dict)

        user_specified = ArenaFighter.TARGETS[self.bot.world_name][level+1]
        if user_specified:
            self.log.debug(gettext('Found user specified heroes: {0}').format(user_specified))

            for targetid in user_specified:
                opponents[level+1][targetid] = dict(u=USER_SPECIFIED, id=targetid)

            if opponents:
                return opponents

        for n in xrange(int(searches)):
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
                        self.log.debug(gettext('Skip {0} as it has beaten us already').format(opp))
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
                    self.log.debug(gettext('Found an opponent at level {0}, stop search').format(lvl))
                    break

        opp = opponent or last_resort[0]
        if opp['u'] is USER_SPECIFIED:
            self.log.info(gettext('Our {0} will fight Hero {1}').format(hero, opp['id']))
        else:
            self.log.info(gettext('Our {0} will fight an opposing {1}').format(hero, Hero(opp)))

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
            # If the opponent name is the same object as the one we declared
            if opponent['u'] is USER_SPECIFIED:
                return opponent
            # <= because hero ranks are ordered strongest first (a-e)
            elif hero.client['rank'] <= rank(opponent['gid']):
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
        self.log.info(gettext('Removed hero "{0}" from "{1}"').format(Hero(opponent), opponent['u']))


class ArenaFighter(FilterableCityTask, Controllable):
    COMMAND = 'fighter'
    INTERVAL = 1800
    VIGOR_BASE = 10
    LOSS = -1
    DRAW = 0
    WIN = 1
    MULTI_HITS = 5
    ALLOW_MULTI_HITS = True
    REBORN_COST = {
        Resource.GOLD: 10000000
    }

    HERO_VIGOR_DEPLETED = 8303

    # item id, vigor quantity
    VIGOR_POTIONS = {
        10: inventory.POTION_OF_VIGOR[0],
        100: inventory.POTION_OF_VIGOR_II[0]
    }

    TARGETS = TargetManager()

    def action_attack(self, event, hero, target, multi=None,
                    buy_vigor=None, reborn=None,
                    stoponlose=1, sleep=(), *args, **kwargs):
        """
        Specify a "hero" and a "target" for it to attack. Flags: "stoponlose", "sleep"
        """

        event.propagate = False
        stoponlose = int(stoponlose)
        _hero = Hero.find(hero, *args, **kwargs)

        if not _hero:
            return

        hero_id, found = None, False
        for city in self.cities(**kwargs):
            try:
                hero = city.hero_manager.get_hero_by_attr(Hero.HERO_ID, _hero['hero_id'])
                if hero:
                    hero_id = hero.stat('id')
                    break
            except KeyError:
                pass

        if not hero_id:
            self.chat.send_message(gettext('Could not find the specified hero'), event=event)
            return

        if sleep:
            sleep = bool(int(sleep))

        self.chat.send_message('{0} has {1} {2} for fighting'.format(hero, \
            hero.data.get(Hero.VIGOR, 0), VIGOR), event=event)

        available_vigor_potions = {}
        exchanged_vigor, desired_vigor = 0, 0
        vigor_potions = sorted(self.VIGOR_POTIONS.keys(), reverse=True)

        if buy_vigor:
            try:
                desired_vigor = abs(int(buy_vigor))
                json = self.bot.item_manager.find(self.VIGOR_POTIONS.values())
                for potion in json['ret']['item']:
                    available_vigor_potions[int(potion['sid'])] = int(potion['num'])
            except ValueError as e:
                self.log.debug(e)

        try:
            self.currently_fighting.add(hero_id)

            multi = multi if multi is not None else self.ALLOW_MULTI_HITS

            while True:
                if hero.stat(Hero.LEVEL) == Hero.MAX_LEVEL:

                    if reborn and city.resource_manager.meet_requirements(self.REBORN_COST, unbrick=True):
                        json = city.hero_manager.use_hero_item(hero, action='reborn')

                        if json['code'] == EmrossWar.SUCCESS:
                            gi = json['ret']['geninfo']
                            hero.data[Hero.LEVEL] = int(gi.get('g_grade', hero.data[Hero.LEVEL]-1))
                            hero.data[Hero.EXPERIENCE] = 0
                            hero.data[Hero.VIGOR] = int(gi['energy'])

                            self.chat.send_message(
                                gettext('{0} is reborn!').format(hero),
                                event=event
                            )
                            continue

                    # Max level still!
                    break

                times = self.MULTI_HITS if multi and hero.stat(Hero.VIGOR, 0) >= self.MULTI_HITS else None

                if hero.stat(Hero.VIGOR, 0) < (self.MULTI_HITS if multi else 1):

                    if exchanged_vigor < desired_vigor:

                        pots = (reward for reward in vigor_potions if desired_vigor - exchanged_vigor > reward)
                        poison = None

                        # Choose our poison
                        for vigor_rewarded in pots:
                            if available_vigor_potions[self.VIGOR_POTIONS[vigor_rewarded]]:
                                # This type of potion is in stock, let's use it!
                                poison = self.VIGOR_POTIONS[vigor_rewarded]
                                break

                        if poison:
                            json = city.hero_manager.use_hero_item(hero, action='energy', itemid=poison)

                            if json['code'] == EmrossWar.SUCCESS:
                                available_vigor_potions[self.VIGOR_POTIONS[vigor_rewarded]] -= 1
                                exchanged_vigor += vigor_rewarded
                                hero.data[Hero.VIGOR] = int(json['ret']['energy'])

                                """
                                Continue to next loop to avoid breakout and
                                recalculate if we can perform a multi-hit
                                """
                                continue

                    # Still allowed to hit between 0 and MULTI_HITS
                    if not hero.data.get(Hero.VIGOR):
                        break

                json = self.attack(hero_id, int(target), sleep=sleep, times=times)

                if json['code'] == self.HERO_VIGOR_DEPLETED:
                    self.log.debug(gettext('Hero vigor looks depleted, do a final check'))
                    city.hero_manager.expire()
                    hero = city.hero_manager.get_hero_by_attr('id', hero_id)
                    continue

                elif json['code'] != EmrossWar.SUCCESS:
                    try:
                        msg = EmrossWar.LANG['ERROR']['SERVER'][str(json['code'])]
                    except KeyError:
                        msg = gettext('Stopping after error {0} occurred!').format(json['code'])
                    self.chat.send_message(msg, event=event)
                    break

                hero.data[Hero.VIGOR] -= max(times, 1)
                hero.data[Hero.EXPERIENCE] += int(json['ret']['exp'])

                if hero.stat(Hero.EXPERIENCE) >= hero.stat(Hero.TARGET_EXPERIENCE):
                    hero.data[Hero.LEVEL] += 1
                    city.hero_manager.expire()

                    self.chat.send_message(gettext('My {0} is now level {1}').format(\
                        hero, hero.stat(Hero.LEVEL)), event=event)

                    continue

                if int(json['ret'].get('lose', 0)) > 0 or json['ret']['win'] <= self.LOSS:
                    if stoponlose:
                        self.chat.send_message('{0} retires after defeat'.format(hero), event=event)
                        break
        finally:
            self.currently_fighting.remove(hero_id)

        self.chat.send_message('{0} has {1} {2} left'.format(hero, \
            hero.stat(Hero.VIGOR, 0), VIGOR), event=event)

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
            return

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
                    messages.append(six.u('{0} ({1}). id={id}, wins={streak}').format(
                        Hero(opponent), opponent['u'],
                        id=opponent['id'], streak=opponent[Hero.WINS]
                    ))

        mailer.send_mail(title, six.u('\n').join(messages), recipient=event.player_name, **kwargs)

    def attack(self, hero, target, **kwargs):
        """
        {"code":0,"ret":{"exp":985,"win":-3}}

        win>0, draw=0, loss<0
        """
        return self.bot.api.call(CONSCRIPT_URL, gid=hero, tgid=target, **kwargs)

    def setup(self):
        self.currently_fighting = set()

    def process(self, below=1, loss_limit=1, allow_multi=None, *args, **kwargs):
        """
        below - how many vigor below max should we stay?
        loss_limit - how many concurrent defeats before deciding target is too strong?
        searches - how many times should we try looking for heroes at a given level?
        """

        max_vigor = self.VIGOR_BASE + (2 * self.bot.alliance.tech(AllyTech.INCENTIVE))
        self.log.debug('Max {0} is {1}'.format(VIGOR, max_vigor))
        below = min(below, max_vigor)

        opponents = OpponentFinder(self.bot)

        cities = self.cities(**kwargs)
        for city in cities:
            for hero in city.hero_manager.ordered_by_stats(stats=[Hero.VIGOR, Hero.LEVEL], descending=False):
                if hero.data.get(Hero.LEVEL) == Hero.MAX_LEVEL:
                    self.log.debug(six.u('Skipping {0}, already MAX level').format(hero))
                    continue

                self.log.info('{0} has {amt} {vigor}. Current streak: {streak}, Total W/L: {win}/{loss}'.format(\
                    hero,
                    amt=hero.data.get(Hero.VIGOR, 0),
                    vigor=VIGOR,
                    streak=hero.data.get(Hero.WINS, 0),
                    win=hero.data.get(Hero.TOTAL_WINS, 0),
                    loss=hero.data.get(Hero.TOTAL_LOSSES, 0)
                    )
                )

                if int(hero.data['id']) in self.currently_fighting:
                    self.log.info(gettext('Skip currently fighting hero, {0}').format(hero))
                    continue

                """
                Iterate the appropriate number of times to reduce remaining
                vigor to maximum vigor less the specified amount below
                """
                tainted = False
                losses = 0
                allow_multi = allow_multi if allow_multi is not None else self.ALLOW_MULTI_HITS

                while hero.data.get(Hero.VIGOR, 0) > (max_vigor - below):

                    if int(hero.data['id']) in self.currently_fighting:
                        self.log.info(gettext('Stop currently fighting hero, {0}').format(hero))
                        break

                    level = hero.data.get(Hero.LEVEL)
                    opponent = opponents.find_arena_opponent(hero, level, **kwargs)

                    times = None
                    sleep = ()

                    if allow_multi and (hero.data.get(Hero.VIGOR, 0) - self.MULTI_HITS) >= (max_vigor - below):
                        sleep = False
                        times = self.MULTI_HITS

                    json = self.attack(hero.data['id'], opponent['id'], times=times, sleep=sleep)

                    if json['code'] != EmrossWar.SUCCESS:
                        break

                    hero.data[Hero.VIGOR] -= max(times, 1)
                    hero.data[Hero.EXPERIENCE] += int(json['ret']['exp'])

                    if 'lose' in json['ret']:
                        losses += int(json['ret']['lose'])

                    elif json['ret']['win'] <= self.LOSS:
                        losses += 1

                    elif losses > 0:
                        losses -= 1

                    if losses >= loss_limit:
                        self.log.info(gettext('Loss limit reached, stopping fighting with {0}').format(hero))
                        opponents.remove_opponent(opponent)
                        break

                    if hero.data.get(Hero.EXPERIENCE) > hero.data.get(Hero.TARGET_EXPERIENCE):
                        tainted = True
                        break


                if tainted:
                    city.hero_manager.expire()
                    self.sleep(5)
