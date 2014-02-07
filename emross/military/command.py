from emross.api import EmrossWar
from emross.arena.hero import Hero
from emross.exceptions import (InsufficientHeroCommand,
    InsufficientSoldiers,
    NoHeroesAvailable)
from emross.military.barracks import Barracks
from emross.military.camp import Soldier
from emross.utility.controllable import Controllable
from emross.utility.task import Task

from lib.ordered_dict import OrderedDict


class CommandCenter(Task, Controllable):
    COMMAND = 'barracks'
    LOOT_COMMAND = 'loot'

    def setup(self):
        # For backwards-compatability
        self.bot.events.subscribe(self.LOOT_COMMAND, self.action_loot)

    def _barracks_action(self, x, y, *args, **kwargs):
        """
        Base behavior of the command center
        """
        nx, ny = self.bot.world.map_size()

        try:
            x, y = int(x), int(y)
            if 1 > x > nx or 1 > y > ny:
                raise ValueError
        except ValueError:
            self.chat.send_message('Are you sure about those co-ordinates?')
            self.log.debug(
                'Invalid co-ordinates provided: x={0}, y={1}'.format(x, y)
            )
            return

        level = kwargs.get('level')
        if level:
            current_lvl = int(self.bot.userinfo.get('level', 0))
            exact_lvl, min_lvl, max_lvl = None, 0, 999
            try:
                if '-' in level:
                    parts = map(int, level.split('-', 1))
                    min_lvl = parts.pop(0)
                    max_lvl = parts.pop(0)
                else:
                    exact_lvl = int(level) == current_lvl
            except (IndexError, ValueError):
                pass

            if exact_lvl is not None:
                if not exact_lvl:
                    self.log.debug('Does not match exact level. Current={0}, specified={1}'.format(current_lvl, level))
                    return
            elif not min_lvl <= current_lvl <= max_lvl:
                self.log.debug('Not within specified level range, stop processing')
                return

        desired = self._parse_desired_troops(**kwargs)

        """
        Can we find the desired army at any of our castles?
        """
        launched = 0
        times = int(kwargs.get('times', 1))
        attack_type = int(kwargs.get('attack_type', Barracks.LOOT))

        for city in self.bot.cities:
            if launched == times:
                break

            try:
                city.barracks.expire()
                troops = []
                for soldier, vals in desired.iteritems():
                    qty, remaining = vals
                    troops.append((soldier, qty))
                    if remaining:
                        troops.append((soldier, Soldier.REMAINING))

                # Currently we use heroes with the lowest possible troop capacity
                city.get_available_heroes(stats=[Hero.COMMAND])

                finished_city = False
                for i in xrange(times-launched):

                    if finished_city:
                        break

                    params = {
                        'action': 'do_war',
                        'attack_type': attack_type,
                        'area': x,
                        'area_x': y
                    }

                    army = city.create_army(troops, mixed=(len(troops)>0))
                    self.log.debug(army)

                    army = kwargs.get('hook_army', lambda _: _)(army)
                    params.update(army)

                    if sum(army.values()) == 0:
                        self.log.debug('There is no army to send from "{0}"'.format(city.name))
                        finished_city = True
                        break

                    if kwargs.get('hero'):
                        hero = city.choose_hero(sum(army.values()))
                        if not hero:
                            self.log.debug('Cannot find a hero to command this army')
                            finished_city = True
                            break
                        params.update({'gen': hero.data['gid'],})

                    # Now the prep-work is done, send stuff
                    json = city.barracks.confirm_and_do(params, sleep_confirm=(1,2), sleep_do=False)

                    if json['code'] == EmrossWar.SUCCESS:
                        launched += 1

                        cd = json['ret']['cd'][0]
                        tm = self.bot.human_friendly_time(cd['secs'])
                        action = kwargs.get('action', 'action {0}'.format(attack_type))
                        self.chat.send_message('{0}({1}): {2}. Time: {3}'.format(\
                            action, launched, cd['ext'], tm))
                    else:
                        error = EmrossWar.LANG['ERROR']['SERVER'][str(json['code'])]
                        self.log.debug('{0}: {1}'.format(city.name,
                            EmrossWar.safe_text(error)
                        ))
                        finished_city = True
                        break

            except (InsufficientHeroCommand, InsufficientSoldiers, NoHeroesAvailable) as e:
                self.log.debug(e)


    def _parse_desired_troops(self, **kwargs):
        """
        Search for known troops types based on kwargs which should arrive as such:
        lonu=60 kahk=200 overlord=40 etc
        """

        try:
            SOLDIER_DATA = getattr(EmrossWar, 'SOLDIER_{0}'.format(self.bot.userinfo['nationid']))
        except (AttributeError, KeyError):
            SOLDIER_DATA = EmrossWar.SOLDIER_1

        desired = OrderedDict()

        self.log.debug(kwargs)
        for kw, val in kwargs.iteritems():
            kw = kw.lower()
            try:
                parts = val.split(',', 1)
                qty = int(parts[0])
                remaining = parts[1:] != []
            except (AttributeError, ValueError):
                continue

            for soldier_id, data in SOLDIER_DATA.iteritems():
                if kw in data.get('name', '').lower():
                    self.log.debug('Search for "{0}"'.format(data['name']))
                    desired[int(soldier_id)] = (qty, remaining)

        return desired

    def action_conquer(self, event, *args, **kwargs):
        """
        Who have I looted that I can now conquer?
        """
        kwargs.update({'action':'Conquer', 'attack_type': Barracks.CONQUER, 'hero':True})
        self._barracks_action(*args, **kwargs)

    def action_loot(self, event, *args, **kwargs):
        """
        Send a hero to lead an army to attack another player
        """
        kwargs.update({'action':'Loot', 'attack_type':Barracks.LOOT, 'hero':True})
        self._barracks_action(*args, **kwargs)

    def action_scout(self, event, *args, **kwargs):
        """
        Send spies to another player
        """

        kwargs.update({'action':'Scout', 'attack_type':Barracks.SCOUT,
            'hook_army': lambda army: {'tai_num': army.get('soldier_num2', 1)}
        })
        self._barracks_action(*args, **kwargs)

    def action_transport(self, event, *args, **kwargs):
        """
        Transport troops to another player
        """
        kwargs.update({'action':'Transport', 'attack_type':Barracks.TRANSPORT})
        self._barracks_action(*args, **kwargs)
