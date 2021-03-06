from __future__ import division

import locale
locale.setlocale(locale.LC_ALL, '')

import math
import re
import time

from lib.cacheable import CacheableData
from lib.session import Session


import emross
from emross.alliance import Alliance
from emross.api import EmrossWar
from emross.chat import Chat
from emross.downtown import City
from emross.exceptions import *
from emross.favourites import Favourites
from emross.gift import GiftCollector, GiftEvents
from emross.item import inventory, item, manager
from emross.lottery import AutoLottery
from emross.mail import AttackMailHandler, ScoutMailHandler, MailException
from emross.mail.mailer import Mailer, MailMan
from emross.resources import Resource
from emross.shop import Shop
from emross.trade.trader import Trade
from emross.utility.about import AboutHelper
from emross.utility.base import EmrossBaseObject
from emross.utility.builder import BuildManager
from emross.utility.pushover import Pushover
from emross.utility import events
from emross.world import World


class EmrossWarBot(EmrossBaseObject, CacheableData):
    PVP_MODE_RE = re.compile('^p\d+\.')
    USERINFO_URL = 'game/get_userinfo_api.php'
    OTHER_USERINFO_URL = 'game/api_get_userinfo2.php'

    STATUS_COMMAND = gettext('status')
    UPTIME_COMMAND = gettext('uptime')
    WEALTH_COMMAND = gettext('wealth')

    TIME_PERIODS = (
        (60, gettext('minute')),
        (3600, gettext('hour')),
        (86400, gettext('day')),
        (86400*7, gettext('week'))
    )

    def __init__(self, api, socket_writer=None, settings=None, *args, **kwargs):
        super(EmrossWarBot, self).__init__(bot=self, time_to_live=60, *args, **kwargs)
        self.lock = emross.defer.DeferredLock()
        self.is_initialised = False
        self.closing = False
        self.blocked = False
        self.runnable = True

        self.api = api
        api.bot = self
        self._socket_writer = socket_writer
        self.settings = settings
        self.error = None

        self.session = Session(self)

        self._world_name = None
        self.pvp = self.PVP_MODE_RE.match(api.game_server) is not None
        self.npc_attack_limit = 3 if not self.pvp else 5

        self.builder = BuildManager(self)
        self.tasks = {}
        self._cities = []

        self.events = self.builder.task(events.EventManager)

        self.about = AboutHelper(self)
        self.alliance = self.builder.task(Alliance)
        self.favourites = self.builder.task(Favourites)
        self.item_manager = self.builder.task(item.Item)
        self.inventory = self.builder.task(manager.InventoryManager)
        self.shop = self.builder.task(Shop)
        self.world = self.builder.task(World)

        self.scout_mail = ScoutMailHandler(self)
        self.war_mail = AttackMailHandler(self)
        self.pushover = Pushover


    def __del__(self):
        self.log.debug(gettext('Clean up bot instance'))

    def __repr__(self):
        try:
            return EmrossWar.safe_text(self._data.get('nick') or str(self.api.player))
        except Exception as e:
            self.log.exception(e)
            return ''

    def disconnect(self, *args, **kwargs):
        self.log.debug(gettext('Disconnecting'))
        self.api.shutdown = True
        self.runnable = False
        self.blocked = True
        self.closing = True

    @emross.defer.inlineCallbacks
    def startup(self):
        now = self.session.start_time = time.time()
        self.log.debug(gettext('Started at %s'), now)
        userinfo = yield self.userinfo
        self.log.debug(gettext('init id=%s'), userinfo['id'])
        self.builder.run(self.tasks)

    def shutdown(self):
        self.closing = True
        self.session.end_time = time.time()
        try:
            self.session.save()
        except IOError:
            self.log.warning(gettext('Error saving session'))

    @property
    def userinfo(self):
        if not self.is_initialised and self.closing:
            raise BotException(gettext('userinfo unavailable and marked for shutdown'))
        return self.data

    def socket_writer(self, data):
        try:
            self._socket_writer.put(data)
        except Exception as e:
            self.log.exception(e)

    @property
    def cities(self):
        return self._cities

    def core_setup(self):
        """
        Some utility functions
        """

        self.tasks['core'] = (
            (
                (Chat,),
                (AutoLottery,),
                (GiftCollector,),
                (GiftEvents,),
            ),
        )

        # Register Controllable modules
        self.builder.task(Mailer)
        self.builder.task(MailMan)
        self.builder.task(Trade)

        if self.api.player:
            if hasattr(self.settings, 'build_path') and \
                self.api.player.disable_global_build == False:

                self.tasks['build_path'] = self.settings.build_path

            if self.api.player.custom_build:
                self.tasks['custom'] = self.api.player.custom_build


        def status(event, precision=3, *args, **kwargs):
            chat = self.builder.task(Chat)

            json = self.api.call(self.USERINFO_URL, action='exp')
            exp_start, exp_end, protection_end = json['ret']

            lvl = '{0}({1}%)'.format(self.userinfo.get('level', 0),
                round(100*(exp_start/exp_end), int(precision))
            )
            parts = [
                ('level', lvl),
                ('gems', self.userinfo.get('money', 0)),
                ('pvp', self.userinfo.get('pvp', 0))
            ]

            conquer = self.userinfo.get('conq', [0, 0, None, 5])
            conqueror_id, conq_end, conq_name, _discard = conquer

            if conqueror_id:
                parts.append((gettext('conquered by'), conq_name))
                f = self.human_friendly_time(conq_end - time.time())
                parts.append((gettext('conquer ends'), f))

            chat.send_message('{0}: {data}'.format(self.STATUS_COMMAND,
                data = ', '.join(['{0}={1}'.format(k,v) for k, v in parts])
            ), event=event)
        self.events.subscribe(self.STATUS_COMMAND, status)

        def uptime(event, *args, **kwargs):
            chat = self.builder.task(Chat)
            f = self.human_friendly_time(time.time() - self.session.start_time)
            chat.send_message('{0}: {1}'.format(gettext('uptime'), f), event=event)
        self.events.subscribe(self.UPTIME_COMMAND, uptime)

        def wealth(event, *args, **kwargs):
            chat = self.builder.task(Chat)
            chat.send_message(self.total_wealth(*args, **kwargs), event=event)
        self.events.subscribe(self.WEALTH_COMMAND, wealth)

    @emross.defer.inlineCallbacks
    def update(self):
        """
        Setup bot with player account data
        """

        self.log.debug(gettext('Updating player info'))
        json = yield self.api.call(self.USERINFO_URL, pushid=self.api.pushid)

        self._data = userinfo = json['ret']['user']

        skip = set([city.id for city in self.cities])
        skip.update(getattr(self.settings, 'ignore_cities', []))
        cities = [city for city in userinfo['city'] if city['id'] not in skip]

        for city in cities:
            city = City(self, city['id'], city['name'], x=city['x'], y=city['y'])
            self.log.debug(gettext('Adding "{0}" ({1}) to city list').format(city.name, city.id))
            self._cities.append(city)

        self.log.debug(
            ngettext('Player has {0} city', 'Player has {0} cities',
                len(self._cities)).format(len(self._cities))
        )

        if not self.is_initialised:
            self.is_initialised = True
            self.core_setup()

        for gift in userinfo['gift']:
            yield self.get_gift(gift)

        emross.defer.returnValue(userinfo)

    @emross.defer.inlineCallbacks
    def get_gift(self, gift):
        gid = gift['id']
        try:
            gift_item = EmrossWar.ITEM[str(gid)]['name']
        except KeyError:
            gift_item = gid

        self.log.info(gettext('Collecting gift "{0}"').format(gift_item))
        json = yield self.api.call(item.Item.ITEM_LIST, action='gift', id=gid)

        if int(gid) == inventory.DAILY_GIFT[0]:
            self.session.last_daily_gift = time.time()
            self.events.notify(events.Event('emross.gift.daily.received'))

        emross.defer.returnValue(json)

    def scout_map(self, **kwargs):
        self.log.info(gettext('Trying to find more targets to attack'))

        try:
            last_scan = self.session.last_scan
        except AttributeError:
            last_scan = 0

        hours = kwargs.get('scouting_interval', 72)
        if time.time() < last_scan + hours*3600:
            self.log.debug(gettext('The world was scanned less than {0} hours ago').format(hours))
        else:
            try:
                self.world.search(**kwargs)
                self.session.last_scan = time.time()
            except OutOfSpies as e:
                self.session.last_scan = 0
                self.log.info(e)
            finally:
                self.session.save()

        try:
            self.log.debug(gettext('Look at scout reports to try to locate devil armies'))
            self.scout_mail.process(**kwargs)
        except MailException:
            pass


    def is_play_time(self, playtimes=None):
        """
        Check if we should be playing at this time of day.
        May not wish to be on 24/7 after all!
        """

        if playtimes is None:
            playtimes = self.api.player.playtimes

        try:
            for timespan in playtimes:
                if timespan[0] <= time.localtime().tm_hour < timespan[1]:
                    return True
        except AttributeError:
            return True

        return False

    @emross.defer.inlineCallbacks
    def _city_wealth(self, func=max, text='most'):

        cities = []
        for _city in self.cities:
            gold = yield _city.resource_manager.get_amount_of(Resource.GOLD)
            cities.append((_city, gold))

        city, total = func(cities, key = lambda c: c[1])

        self.log.debug(gettext('Chosen the city with the {0} {resource}, {city} ({amount})').format(text,
            resource=EmrossWar.LANG.get('COIN', 'gold'),
            city=city, amount=total)
        )

        emross.defer.returnValue(city)

    def richest_city(self):
        return self._city_wealth(max, 'most')

    def poorest_city(self):
        return self._city_wealth(min, 'least')

    def clean_war_reports(self, **kwargs):
        try:
            self.war_mail.process(**kwargs)
        except MailException:
            pass

    def clearout_inventory(self, city=None, use_items=False, sell_items=False, **kwargs):
        self.log.debug(gettext('Clear the item inventories'))

        it = item.ItemType
        for itype in [it.WEAPON, it.ARMOR, it.RING, it.MOUNT, it.BOOK]:
            page = 1
            sale_list = []

            self.log.debug(gettext('Find items of type {0}').format(itype))
            while True:
                json = yield self.item_manager.list(page=page, type=itype)

                for _item in json['ret']['item']:
                    try:
                        if item.ITEMS[_item['item']['sid']]['rank'] < item.ItemRank.RARE:
                            sale_list.append(_item['item']['id'])
                    except KeyError:
                        pass


                page += 1
                if page > json['ret']['max']:
                    self.log.debug(gettext('Last page of item type {0}').format(itype))
                    break

            if sale_list:
                self.log.debug(gettext('Sell {0} item/s of type {1}').format(len(sale_list), itype))
                if not city:
                    city = yield self.poorest_city()

                for item_id in sale_list:
                    try:
                        json = yield self.item_manager.sell(city=city, id=item_id)
                        city.resource_manager.set_amount_of(Resource.GOLD, json['ret']['gold'])
                    except (KeyError, TypeError):
                        pass

                sale_list[:] = []


        for can_process, _items, func in [
            (use_items, inventory.USABLE_ITEMS, self.item_manager.use),
            (sell_items, inventory.SELLABLE_ITEMS, self.item_manager.sell)
            ]:

            if not can_process:
                continue

            result = yield self.find_inventory_items(_items)

            for sid, found_items in result.iteritems():
                for item_id, num, val in found_items:
                    if not city:
                        city = yield self.poorest_city()
                    yield func(city=city.id, id=item_id, num=num)


    @emross.defer.inlineCallbacks
    def find_inventory_item(self, search_item):
        item_id, item_type, item_rank = search_item
        items = yield self.find_inventory_items([item_id])
        emross.defer.returnValue(items.get(item_id))

    @emross.defer.inlineCallbacks
    def find_inventory_items(self, items):
        result = {}

        for sid in items:
            try:
                _search = EmrossWar.ITEM[str(sid)]
            except AttributeError:
                data = yield self.inventory.data
                _search = data[sid].values()
                self.log.debug(_search)
                # Choose the first one
                _search = _search.pop(0)['item']

            try:
                self.log.debug(gettext('Searching for item {0}: "{1}"').format(\
                    sid, _search.get('name', 'Unknown')
                ))

                data = yield self.inventory.data
                result[sid] = [
                    [_item['item']['id'], _item['item']['num'], _item['sale']]
                    for _item in data[sid].itervalues()
                ]
            except KeyError:
                pass

        emross.defer.returnValue(result)

    @emross.defer.inlineCallbacks
    def find_gold_for_city(self, city, gold, unbrick=False):
        """
        Given a city, try to find any items we have that we can sell for gold.
        """
        sellable_items = []

        total_amount = lambda: sum([qty*price for id, qty, price in sellable_items])

        if total_amount() < gold and unbrick:
            items = yield self.find_inventory_items([
                inventory.GOLD_BRICK[0], inventory.GOLD_BULLION[0]
            ])
            [sellable_items.extend(v) for v in items.itervalues()]

        if total_amount() < gold:
            emross.defer.returnValue(False)

        total = 0
        for item_id, qty, price in sellable_items:
            remaining = gold - total
            num = math.ceil(remaining / price)
            num = int(min(num, qty))

            kwargs = {}
            if num > 1:
                kwargs['num'] = num

            json = yield self.item_manager.sell(city=city, id=item_id, **kwargs)

            if json['code'] == EmrossWar.SUCCESS:
                city.resource_manager.set_amount_of(Resource.GOLD, json['ret']['gold'])
                total += num*price

            if total >= gold:
                emross.defer.returnValue(True)

        emross.defer.returnValue(False)

    @emross.defer.inlineCallbacks
    def total_wealth(self, bricked=None, **kwargs):
        coin = EmrossWar.LANG.get('COIN', 'gold')
        parts = []
        parts.append('Total {0} amongst all castles: {1}'.format(coin, \
                locale.format('%d',
                    sum([c.get_gold_count()[0] for c in self.cities]), True
                )))

        if bricked:
            bricks = [inventory.GOLD_BULLION[0], inventory.GOLD_BRICK[0]]
            _items = yield self.find_inventory_items(bricks)

            for brick in bricks:
                if brick in _items:
                    parts.append('{0}={1}'.format(EmrossWar.ITEM[str(brick)].get('name'),\
                        sum([qty for item_id, qty, price in _items[brick]])))

        emross.defer.returnValue(', '.join(parts))

    @property
    def minimum_food(self):
        if self.api.player and self.api.player.minimum_food > 0:
            return self.api.player.minimum_food

        return getattr(self.settings, 'minimum_food', 0)

    @property
    def operators(self):
        ops = emross.OPERATORS[:]
        try:
            ops.extend(self.api.player.operators)
        except Exception:
            pass
        return ops

    def human_friendly_time(self, seconds):
        num, duration = 0, long(round(seconds))
        runtime = []
        for period, unit in self.TIME_PERIODS[::-1]:
            num, duration = divmod(duration, period)
            if num:
                p = '{0}{1}'.format(unit, 's'*(num!=1))
                runtime.append('{0} {1}'.format(num, p))

        runtime.append('{0} second{1}'.format(duration, 's'*(duration!=1)))

        return ', '.join(runtime)

    @emross.defer.inlineCallbacks
    def other_player_info(self, id=None, **kwargs):
        if id:
            json = yield self.api.call(self.OTHER_USERINFO_URL, id=id, **kwargs)
            emross.defer.returnValue(json)

    @property
    @emross.defer.inlineCallbacks
    def world_name(self):
        """
        Query the game world only once per run
        """
        if not self._world_name:
            json = yield self.api.call(EmrossWar.CONFIG.get('MASTER_NAMING', 'naming.php'), EmrossWar.MASTER_HOST, s=self.api.game_server, key=None)
            if json['code'] == EmrossWar.SUCCESS:
                self._world_name = json['ret']

        emross.defer.returnValue(self._world_name)
