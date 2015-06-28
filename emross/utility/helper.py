from __future__ import division
from lib import six

import locale
locale.setlocale(locale.LC_ALL, '')

import math
import re
import time

from multiprocessing.dummy import RLock

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

    STATUS_COMMAND = _('status')
    UPTIME_COMMAND = _('uptime')
    WEALTH_COMMAND = _('wealth')

    def __init__(self, api, socket_writer=None, settings=None, *args, **kwargs):
        super(EmrossWarBot, self).__init__(bot=self, time_to_live=60, *args, **kwargs)
        self.lock = RLock()
        self.is_initialised = False
        self.closing = False
        self.blocked = False
        self.runnable = True

        self.api = api
        api.bot = self
        self._socket_writer = socket_writer
        self.settings = settings
        self.errors = six.moves.queue.Queue()

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
        self.log.debug(_('Clean up bot instance'))

    def __repr__(self):
        try:
            return EmrossWar.safe_text(self._data.get('nick') or str(self.api.player))
        except Exception as e:
            self.log.exception(e)
            return ''

    def disconnect(self, *args, **kwargs):
        self.log.debug(_('Disconnecting'))
        self.api.shutdown = True
        self.runnable = False
        self.blocked = True
        self.closing = True

    def shutdown(self):
        self.closing = True
        self.session.end_time = time.time()
        try:
            self.session.save()
        except IOError:
            self.log.warning(_('Error saving session'))

    @property
    def userinfo(self):
        if not self.is_initialised and self.closing:
            raise BotException(_('userinfo unavailable and marked for shutdown'))
        return self.data

    def socket_writer(self, data):
        try:
            self._socket_writer.put(data)
        except Exception as e:
            self.log.exception(e)

    @property
    def cities(self):
        with self.lock:
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
                parts.append((_('conquered by'), conq_name))
                f = self.human_friendly_time(conq_end - time.time())
                parts.append((_('conquer ends'), f))

            chat.send_message('{0}: {data}'.format(self.STATUS_COMMAND,
                data = ', '.join(['{0}={1}'.format(k,v) for k, v in parts])
            ), event=event)
        self.events.subscribe(self.STATUS_COMMAND, status)

        def uptime(event, *args, **kwargs):
            chat = self.builder.task(Chat)
            f = self.human_friendly_time(time.time() - self.session.start_time)
            chat.send_message('uptime: {0}'.format(f), event=event)
        self.events.subscribe(self.UPTIME_COMMAND, uptime)

        def wealth(event, *args, **kwargs):
            chat = self.builder.task(Chat)
            chat.send_message(self.total_wealth(*args, **kwargs), event=event)
        self.events.subscribe(self.WEALTH_COMMAND, wealth)

    def update(self):
        """
        Setup bot with player account data
        """

        self.log.debug(_('Updating player info'))
        json = self.api.call(self.USERINFO_URL, pushid=self.api.pushid)

        self._data = userinfo = json['ret']['user']

        skip = set([city.id for city in self.cities])
        skip.update(getattr(self.settings, 'ignore_cities', []))
        cities = [city for city in userinfo['city'] if city['id'] not in skip]

        for city in cities:
            city = City(self, city['id'], city['name'], x=city['x'], y=city['y'])
            self.log.debug(six.u('Adding "{0}" ({1}) to city list').format(city.name, city.id))
            self._cities.append(city)

        if not self.is_initialised:
            self.is_initialised = True
            self.core_setup()

        for gift in userinfo['gift']:
            self.get_gift(gift)

        return userinfo

    def get_gift(self, gift):
        gid = gift['id']
        try:
            gift_item = EmrossWar.ITEM[str(gid)]['name']
        except KeyError:
            gift_item = gid

        self.log.info(_('Collecting gift "{0}"').format(gift_item))
        json = self.api.call(item.Item.ITEM_LIST, action='gift', id=gid)

        if int(gid) == inventory.DAILY_GIFT[0]:
            self.session.last_daily_gift = time.time()
            self.events.notify(events.Event('emross.gift.daily.received'))

        return json

    def scout_map(self, **kwargs):
        self.log.info(_('Trying to find more targets to attack'))

        try:
            last_scan = self.session.last_scan
        except AttributeError:
            last_scan = 0

        hours = kwargs.get('scouting_interval', 72)
        if time.time() < last_scan + hours*3600:
            self.log.debug(_('The world was scanned less than {0} hours ago').format(hours))
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
            self.log.debug(_('Look at scout reports to try to locate devil armies'))
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

    def _city_wealth(self, func=max, text='most'):
        city = func(self.cities, key = lambda c: c.resource_manager.get_amount_of(Resource.GOLD))
        self.log.debug(six.u('Chosen the city with the {0} {resource}, {city} ({amount})').format(text,
            resource=EmrossWar.LANG.get('COIN', 'gold'),
            city=city, amount=city.resource_manager.get_amount_of(Resource.GOLD))
        )
        return city

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
        self.log.debug(_('Clear the item inventories'))

        it = item.ItemType
        for itype in [it.WEAPON, it.ARMOR, it.RING, it.MOUNT, it.BOOK]:
            page = 1
            sale_list = []

            self.log.debug(_('Find items of type {0}').format(itype))
            while True:
                json = self.item_manager.list(page=page, type=itype)

                for _item in json['ret']['item']:
                    try:
                        if item.ITEMS[_item['item']['sid']]['rank'] < item.ItemRank.RARE:
                            sale_list.append(_item['item']['id'])
                    except KeyError:
                        pass


                page += 1
                if page > json['ret']['max']:
                    self.log.debug(_('Last page of item type {0}').format(itype))
                    break

            if sale_list:
                self.log.debug(_('Sell {0} item/s of type {1}').format(len(sale_list), itype))
                city = city or self.poorest_city()

                for item_id in sale_list:
                    try:
                        json = self.item_manager.sell(city=city, id=item_id)
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

            result = self.find_inventory_items(_items)

            for sid, found_items in result.iteritems():
                for item_id, num, val in found_items:
                    city = city or self.poorest_city()
                    func(city=city.id, id=item_id, num=num)


    def find_inventory_item(self, search_item):
        item_id, item_type, item_rank = search_item
        return self.find_inventory_items([item_id]).get(item_id)

    def find_inventory_items(self, items):
        result = {}

        for sid in items:
            try:
                _search = EmrossWar.ITEM[str(sid)]
            except AttributeError:
                _search = self.inventory.data[sid].values()
                self.log.debug(_search)
                # Choose the first one
                _search = _search.pop(0)['item']

            try:
                self.log.debug(_('Searching for item {0}: "{1}"').format(\
                    sid, _search.get('name', 'Unknown')
                ))

                result[sid] = [
                    [_item['item']['id'], _item['item']['num'], _item['sale']]
                    for _item in self.inventory.data[sid].itervalues()
                ]
            except KeyError:
                pass

        return result

    def find_gold_for_city(self, city, gold, unbrick=False):
        """
        Given a city, try to find any items we have that we can sell for gold.
        """
        sellable_items = []

        total_amount = lambda: sum([qty*price for id, qty, price in sellable_items])

        if total_amount() < gold and unbrick:
            items = self.find_inventory_items([
                inventory.GOLD_BRICK[0], inventory.GOLD_BULLION[0]
            ])
            [sellable_items.extend(v) for v in items.itervalues()]

        if total_amount() < gold:
            return False

        total = 0
        for item_id, qty, price in sellable_items:
            remaining = gold - total
            num = math.ceil(remaining / price)
            num = int(min(num, qty))

            kwargs = {}
            if num > 1:
                kwargs['num'] = num

            json = self.item_manager.sell(city=city, id=item_id, **kwargs)

            if json['code'] == EmrossWar.SUCCESS:
                city.resource_manager.set_amount_of(Resource.GOLD, json['ret']['gold'])
                total += num*price

            if total >= gold:
                return True

        return False

    def total_wealth(self, bricked=None, **kwargs):
        coin = EmrossWar.LANG.get('COIN', 'gold')
        parts = []
        parts.append('Total {0} amongst all castles: {1}'.format(coin, \
                locale.format('%d',
                    sum([c.get_gold_count()[0] for c in self.cities]), True
                )))

        if bricked:
            bricks = [inventory.GOLD_BULLION[0], inventory.GOLD_BRICK[0]]
            _items = self.find_inventory_items(bricks)

            for brick in bricks:
                if brick in _items:
                    parts.append('{0}={1}'.format(EmrossWar.ITEM[str(brick)].get('name'),\
                        sum([qty for item_id, qty, price in _items[brick]])))

        return ', '.join(parts)

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
        for period, unit in [(60, 'minute'), (3600, 'hour'), (86400, 'day'), (86400*7, 'week')][::-1]:
            num, duration = divmod(duration, period)
            if num:
                p = '{0}{1}'.format(unit, 's'*(num!=1))
                runtime.append('{0} {1}'.format(num, p))

        runtime.append('{0} second{1}'.format(duration, 's'*(duration!=1)))

        return ', '.join(runtime)

    def other_player_info(self, id=None, **kwargs):
        if id:
            return self.api.call(self.OTHER_USERINFO_URL, id=id, **kwargs)

    @property
    def world_name(self):
        """
        Query the game world only once per run
        """
        if not self._world_name:
            json = self.api.call('naming.php', emross.master, s=self.api.game_server)
            if json['code'] == EmrossWar.SUCCESS:
                self._world_name = json['ret']

        return self._world_name
