from emross.api import EmrossWar
from emross.arena.hero import Hero
from emross.chat import Chat
from emross.exceptions import (InsufficientHeroCommand,
    InsufficientSoldiers,
    NoHeroesAvailable)
from emross.military.barracks import Barracks
from emross.military.camp import Soldier
from emross.utility.task import Task

from lib.ordered_dict import OrderedDict

LOOT_COMMAND = 'loot'


class CommandCenter(Task):
    def setup(self):
        self.bot.events.subscribe(LOOT_COMMAND, self.loot)
        self.chat = self.bot.builder.task(Chat)

    def process(self, *args, **kwargs):
        """
        Dummy!
        """
        pass

    def loot(self, x, y, level=None, times=1, *args, **kwargs):
        nx, ny = self.bot.world.map_size()

        try:
            x, y = int(x), int(y)
            if 1 > x > nx or 1 > y > ny:
                raise ValueError
        except ValueError:
            self.chat.send_message('Are you sure about those co-ordinates?')
            return

        if level:
            current_lvl = self.bot.userinfo.get('level', 1)
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

        try:
            SOLDIER_DATA = getattr(EmrossWar, 'SOLDIER_{0}'.format(self.bot.userinfo['nationid']))
        except (AttributeError, KeyError):
            SOLDIER_DATA = EmrossWar.SOLDIER_1

        desired = OrderedDict()
        for kw, val in kwargs.iteritems():
            kw = kw.lower()
            try:
                parts = val.split(',', 1)
                qty = int(parts[0])
                remaining = parts[1:] != []
            except ValueError:
                continue

            for soldier_id, data in SOLDIER_DATA.iteritems():
                if kw in data.get('name', '').lower():
                    self.log.info('Search for "{0}"'.format(data['name']))
                    desired[int(soldier_id)] = (qty, remaining)

        """
        Can we find the desired army at any of our castles?
        """
        accomplished = False
        launched = 0
        times = int(times)
        for city in self.bot.cities:
            if launched == times:
                break

            try:
                city.barracks.camp_info()
                troops = []
                for soldier, vals in desired.iteritems():
                    qty, remaining = vals
                    troops.append((soldier, qty))
                    if remaining:
                        troops.append((soldier, Soldier.REMAINING))

                # Currently we use heroes with the lowest possible troop capacity
                city.get_available_heroes(stats=[Hero.COMMAND])

                for i in xrange(times-launched):
                    army = city.create_army(troops, mixed=(len(troops)>0))
                    self.log.debug(army)

                    hero = city.choose_hero(sum(army.values()))
                    if not hero:
                        self.log.debug('Cannot find a hero to command this army')
                        break

                    json = self._send_attack(x, y, city, hero, **army)
                    if json['code'] == EmrossWar.SUCCESS:
                        accomplished = True
                        launched += 1

                        cd = json['ret']['cd'][0]
                        tm = self.bot.human_friendly_time(cd['secs'])
                        self.chat.send_message('Loot({0}): {1}. Impact: {2}'.format(launched, cd['ext'], tm))
                    else:
                        break

            except (InsufficientHeroCommand, InsufficientSoldiers, NoHeroesAvailable) as e:
                self.log.debug(e)

        if not accomplished:
            self.chat.send_message('Sorry, I was not able to meet the loot requirements.')


    def _send_attack(self, x, y, city, hero, attack_type=Barracks.LOOT, **kwargs):
        # as ever, x and y are backwards just to confise things!
        params = {
            'action': 'do_war',
            'attack_type': attack_type,
            'gen': hero.data['gid'],
            'area': x,
            'area_x': y
        }
        params.update(kwargs)

        return city.barracks.confirm_and_do(params, sleep_confirm=(1,2), sleep_do=False)
