from __future__ import division
from lib import six

import math

from lib.cacheable import CacheableData

from emross.api import EmrossWar
from emross.arena import CONSCRIPT_URL, CONSCRIPT_GEAR_URL
from emross.arena.hero import Gear, Hero
from emross.arena.fighter import ArenaFighter
from emross.structures.buildings import Building
from emross.structures.construction import Construct
from emross.utility.controllable import Controllable


class HeroManager(Controllable, CacheableData):
    COMMAND = 'heroes'

    def __init__(self, bot, city):
        super(HeroManager, self).__init__(bot)
        self.city = city
        self._heroes = {}

    @property
    def heroes(self):
        _ = self.data
        return self._heroes

    def action_fighter(self, event, *args, **kwargs):
        event.propagate = False
        self.bot.builder.task(ArenaFighter)._controller(event, *args, **kwargs)

    def action_status(self, event, *args, **kwargs):
        """
        Find the specified hero.
        """
        hero = Hero.find(*args, **kwargs)

        if hero:
            event.propagate = False
            find_id = hero['hero_id']

            for h in self.heroes.itervalues():
                if int(h.data.get('gid')) == find_id:
                    # Just spit out whatever data we got back
                    if 'debug' in kwargs:
                        self.chat.send_message('Hero data: {0}'.format(h.data))
                        break

                    s = str(h.stat(Hero.STATE))
                    state = EmrossWar.LANG['HEROSTATE'].get(s)
                    message = ['{0}'.format(self.city.name)]
                    message.append('{0}: {1}'.format(h.client.get('name'), state or s))

                    if int(h.stat(Hero.GUARDING)):
                        message.append(EmrossWar.LANG['HEROGUARD'])

                    message.append('{0}={1}'.format(EmrossWar.LANG['LEVEL'], h.stat(Hero.LEVEL)))
                    message.append('{0}={1}'.format(EmrossWar.LANG['ATTACK'], h.stat(Hero.ATTACK)))
                    message.append('{0}={1}'.format(EmrossWar.LANG['WISDOM'], h.stat(Hero.WISDOM)))
                    message.append('{0}={1}'.format(EmrossWar.LANG['DEFENSE'], h.stat(Hero.DEFENSE)))
                    message.append('{0}={1}'.format(EmrossWar.LANG['MAXTROOP'], h.stat(Hero.COMMAND)))
                    message.append('{0}={1}%'.format('exp', \
                        round((h.stat(Hero.EXPERIENCE) / h.stat(Hero.TARGET_EXPERIENCE)) * 100,
                            int(kwargs.get('precision', 3))),
                    ))

                    if 'gear' in kwargs:
                        for _item in h.gear.itervalues():
                            try:
                                gear = EmrossWar.ITEM[_item['item']['sid']]
                                up = int(_item['item']['up'])
                                message.append('{0}(+{1})'.format(gear['name'], up))
                            except KeyError as e:
                                self.log.exception(e)

                    self.chat.send_message(', '.join(message))
                    break

    def _hero_gear_handler(self, hero_id):
        def _update(*args, **kwargs):
            json = self.bot.api.call(*args, **kwargs)
            gear = {}

            if json['code'] == EmrossWar.SUCCESS:
                for _item in json['ret']['heroitem']:
                    item = EmrossWar.ITEM[_item['item']['sid']]
                    gear[Gear.TYPE_SLOTS[int(item['type'])]] = _item

            return gear


        return CacheableData(update=_update, method=CONSCRIPT_GEAR_URL, \
                action='list_gen_item', id=hero_id, city=self.city.id)

    def equip_hero_slot_item(self, hero, slot=2, item_id=-1):
        """
        Equip
        Slots
        """
        json = self.bot.api.call(CONSCRIPT_GEAR_URL,
            action='item_equip',
            id=hero.data['id'],
            i_id=item_id,
            slot=slot,
            city=self.city.id)

        if json['code'] == EmrossWar.SUCCESS:
            hero.update(json['ret']['hero'])

        return json

    def list_hero_slot_items(self, hero, slot=2):
        return self.bot.api.call(CONSCRIPT_GEAR_URL,
            action='list_item',
            id=hero.data['id'],
            slot=slot,
            city=self.city.id)

    def update(self):
        self.log.debug(six.u('Update heroes at {0}').format(self.city))

        json = self.bot.api.call(CONSCRIPT_URL, city=self.city.id, action='gen_list')

        if json['code'] == EmrossWar.SUCCESS:
            heroes = set()
            for hero_data in json['ret']['hero']:
                hero_id = int(hero_data['id'])
                heroes.add(hero_id)
                try:
                    self._heroes[hero_id].update(hero_data)
                except KeyError:
                    self._heroes[hero_id] = Hero(hero_data, \
                        gear=self._hero_gear_handler(hero_id))

            # Remove heroes which are not present
            old_heroes = set(self._heroes.keys())-heroes
            for hero in old_heroes:
                del self._heroes[hero]

            return json

    def highest_stat_hero(self, stat=Hero.COMMAND):
        try:
            hero = self.ordered_by_stats(stats=(stat,))[0]
            self.log.debug(hero)
            attr_name = Hero.ATTRIBUTE_NAMES.get(stat, 'UNKNOWN')
            self.log.debug('{0} with {1} {2}'.format(hero, hero.data.get(stat), attr_name))
            return hero
        except IndexError:
            pass

    def ordered_by_stats(self, stats=[Hero.LEVEL, Hero.EXPERIENCE], exclude=[], descending=True):
        exclude = set(exclude)
        heroes = [hero for hero in self.heroes.values() if hero.stat('gid') not in exclude]
        heroes.sort(key=lambda hero: [hero.data.get(stat) for stat in stats], reverse=descending)
        return heroes

    def ordered_by_scored_stats(self, scoring=[(Hero.COMMAND, 1)], heroes=None, exclude=[]):
        result = []
        exclude = set(exclude)
        heroes = self.heroes if heroes is None else heroes

        for hero_id, hero in heroes.iteritems():
            if hero_id in exclude:
                self.log.debug('Exclude hero {0}'.format(hero_id))
                continue

            score = 0
            for stat, weight in scoring:
                score += hero.data.get(stat, 0) * weight
            result.append((hero, score))

        result.sort(key = lambda hero: hero[1], reverse=True)
        self.log.debug(result)

        return result

    @property
    def remaining_hero_capacity(self):
        """
        How many more heroes do we have space to hold at this arena?
        """
        arena = self.bot.builder.task(Construct).structure_level(self.city, Building.ARENA)
        capacity = math.ceil(arena / 2)
        remaining = int(capacity - len(self.heroes))
        self.log.debug(six.u('{0} remaining hero slots at {1}').format(remaining, self.city))
        return remaining

    def revive_hero(self, hero):
        """
        Given a hero, try reviving it from the dead!
        """
        self.log.debug(six.u('Try to revive {0} at {1}').format(hero, self.city))
        json = self.bot.api.call(CONSCRIPT_GEAR_URL, id=hero.data['id'], action='relive', city=self.city.id)

        if json['code'] == EmrossWar.SUCCESS:
            self.log.info(six.u('Revived {0} at {1}').format(hero, self.city))
            hero.data[Hero.STATE] = Hero.AVAILABLE

        return json
