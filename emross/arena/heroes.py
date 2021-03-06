from __future__ import division
from lib import six

import math

from lib.cacheable import CacheableData

import emross
from emross.api import EmrossWar
from emross.arena import CONSCRIPT_URL, CONSCRIPT_GEAR_URL
from emross.arena.hero import Gear, Hero
from emross.arena.fighter import ArenaFighter
from emross.resources import Resource
from emross.structures.buildings import Building
from emross.structures.construction import Construct
from emross.utility.controllable import Controllable


class HeroManager(Controllable, CacheableData):
    COMMAND = 'heroes'

    REBORN_COST = {
        Resource.GOLD: 10000000
    }

    def __init__(self, bot, city):
        super(HeroManager, self).__init__(bot)
        self.city = city
        self._heroes = {}

    @property
    @emross.defer.inlineCallbacks
    def heroes(self):
        yield self.data
        emross.defer.returnValue(self._heroes)

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
                    message = [six.u('{0}').format(self.city.name)]
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
        @emross.defer.inlineCallbacks
        def _update(*args, **kwargs):
            json = yield self.bot.api.call(*args, **kwargs)
            gear = {}

            if json['code'] == EmrossWar.SUCCESS:
                for _item in json['ret']['heroitem']:
                    item = EmrossWar.ITEM[_item['item']['sid']]
                    gear[Gear.TYPE_SLOTS[int(item['type'])]] = _item

            emross.defer.returnValue(gear)


        return CacheableData(update=_update, method=CONSCRIPT_GEAR_URL, \
                action='list_gen_item', id=hero_id, city=self.city.id)

    @emross.defer.inlineCallbacks
    def equip_hero_slot_item(self, hero, slot=2, item_id=-1):
        """
        Equip
        Slots
        """
        json = yield self.bot.api.call(CONSCRIPT_GEAR_URL,
            action='item_equip',
            id=hero.data['id'],
            i_id=item_id,
            slot=slot,
            city=self.city.id)

        if json['code'] == EmrossWar.SUCCESS:
            hero.update(json['ret']['hero'])

        emross.defer.returnValue(json)

    @emross.defer.inlineCallbacks
    def list_hero_slot_items(self, hero, slot=2):
        json = yield self.bot.api.call(CONSCRIPT_GEAR_URL,
            action='list_item',
            id=hero.data['id'],
            slot=slot,
            city=self.city.id)

        emross.defer.returnValue(json)

    @emross.defer.inlineCallbacks
    def update(self):
        self.log.debug(six.u('Update heroes at {0}').format(self.city))

        json = yield self.bot.api.call(CONSCRIPT_URL, city=self.city.id, action='gen_list')

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

            emross.defer.returnValue(json)

    @emross.defer.inlineCallbacks
    def get_hero_by_attr(self, attr, value=None):
        heroes = yield self.heroes
        for hero in heroes.itervalues():
            if hero.stat(attr) == value:
                emross.defer.returnValue(hero)

    @emross.defer.inlineCallbacks
    def highest_stat_hero(self, stat=Hero.COMMAND):
        try:
            ordered = yield self.ordered_by_stats(stats=(stat,))
            hero = ordered[0]
            self.log.debug(hero)
            attr_name = Hero.ATTRIBUTE_NAMES.get(stat, 'UNKNOWN')
            self.log.debug('{0} with {1} {2}'.format(hero, hero.data.get(stat), attr_name))
            emross.defer.returnValue(hero)
        except IndexError:
            pass

    @emross.defer.inlineCallbacks
    def ordered_by_stats(self, stats=[Hero.LEVEL, Hero.EXPERIENCE], exclude=[], descending=True):
        exclude = set(exclude)
        _heroes = yield self.heroes
        heroes = [hero for hero in _heroes.values() if hero.stat('gid') not in exclude]
        heroes.sort(key=lambda hero: [hero.data.get(stat) for stat in stats], reverse=descending)
        emross.defer.returnValue(heroes)

    @emross.defer.inlineCallbacks
    def ordered_by_scored_stats(self, scoring=[(Hero.COMMAND, 1)], heroes=None, exclude=[]):
        result = []
        exclude = set(exclude)
        if heroes is None:
            heroes = yield self.heroes

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

        emross.defer.returnValue(result)

    @property
    @emross.defer.inlineCallbacks
    def remaining_hero_capacity(self):
        """
        How many more heroes do we have space to hold at this arena?
        """
        arena = yield self.bot.builder.task(Construct).structure_level(self.city, Building.ARENA)
        capacity = math.ceil(arena / 2)
        remaining = int(capacity - len(self.heroes))
        self.log.debug(six.u('{0} remaining hero slots at {1}').format(remaining, self.city))
        emross.defer.returnValue(remaining)

    @emross.defer.inlineCallbacks
    def reborn_hero(self, hero):

        reborn = yield hero.can_reborn()
        requirements_met = yield self.city.resource_manager.meet_requirements(self.REBORN_COST, unbrick=reborn)
        if reborn and requirements_met:
            json = yield self.use_hero_item(hero, action='reborn')
            """
            {'code': 0, 'ret': {'geninfo':
                {'g_liftblood': '0',
                'extra': '{"tianfu_temp":"7"}',
                'energy': '85',
                'reborn': '1',
                'n_intellect': '74',
                'g_power': 483,
                'bf_command': '0',
                'n_power': '461',
                'g_cid': 'HERO_CITY_ID',
                'g_command': 2998, 'id': 'UNIQUE_HERO_ID',
                'n_commend': '339', 'n_status': '0',
                'user_if': '0', 'n_cd': '0', 'g_fy': '0',
                'g_recovery': '124480',
                'tlose': '0', 'g_gid': '335', 'g_grade': '37',
                'largess_times': '1441414339',
                'tianfu': '5',
                'largess_num': '5',
                'g_commend': 362, 'g_uid': 'UNIQUE_USER_ID', 'g_intellect': 79, 'g_speed': '1.08',
                'twin': '25905', 'g_exploit': '0', 'n_command': '2612', 'wins': '25905', 'g_status': '0',
                'g_name': 'Rookie', 'g_fealty': '75'},
                'cost_gold': 10000000}
            }
            """

            if json['code'] == EmrossWar.SUCCESS:
                gi = json['ret']['geninfo']
                hero.data[Hero.LEVEL] = int(gi.get('g_grade', hero.data[Hero.LEVEL]-1))
                hero.data[Hero.EXPERIENCE] = 0
                hero.data['showReborn'] = False
                hero.data[Hero.REBORN] = gi['reborn']
                hero.data[Hero.VIGOR] = int(gi['energy'])

        emross.defer.returnValue(hero)

    @emross.defer.inlineCallbacks
    def revive_hero(self, hero):
        """
        Given a hero, try reviving it from the dead!
        """
        self.log.debug(six.u('Try to revive {0} at {1}').format(hero, self.city))
        json = yield self.bot.api.call(CONSCRIPT_GEAR_URL, id=hero.data['id'], action='relive', city=self.city.id)

        if json['code'] == EmrossWar.SUCCESS:
            self.log.info(six.u('Revived {0} at {1}').format(hero, self.city))
            hero.data[Hero.STATE] = Hero.AVAILABLE

        emross.defer.returnValue(json)

    @emross.defer.inlineCallbacks
    def use_hero_item(self, hero, **kwargs):

        params = dict(id=hero.data['id'], city=self.city.id)
        params.update(kwargs)

        json = yield self.bot.api.call(CONSCRIPT_GEAR_URL, **params)
        emross.defer.returnValue(json)
