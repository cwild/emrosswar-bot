from __future__ import division

import locale
import logging
import math
import re
import time
import Queue
import sys
sys.path.extend(['lib/urllib3/'])

from lib.cacheable import CacheableData
from lib.session import Session


from emross import OPERATORS
from emross.alliance import Alliance
from emross.api import EmrossWar
from emross.chat import Chat
from emross.downtown import City
from emross.exceptions import *
from emross.favourites import Favourites
from emross.gift import GiftCollector, GiftEvents
from emross.item import inventory, item
from emross.lottery import AutoLottery
from emross.mail import AttackMailHandler, ScoutMailHandler, MailException
from emross.resources import Resource
from emross.shop import Shop
from emross.utility.builder import BuildManager
from emross.utility import events
from emross.world import World

import settings

locale.setlocale(locale.LC_ALL, '')
logger = logging.getLogger(__name__)

class EmrossWarBot(CacheableData):
    PVP_MODE_RE = re.compile('^p\d+\.')
    USERINFO_URL = 'game/get_userinfo_api.php'
    OTHER_USERINFO_URL = 'game/api_get_userinfo2.php'

    INVENTORY_COMMAND = 'inventory'
    STATUS_COMMAND = 'status'
    UPTIME_COMMAND = 'uptime'
    WEALTH_COMMAND = 'wealth'

    def __init__(self, api, *args, **kwargs):
        super(EmrossWarBot, self).__init__(time_to_live=60, *args, **kwargs)
        self.is_initialised = False
        self._closing = False
        self.blocked = False
        self.runnable = True

        self.api = api
        api.bot = self
        self.errors = Queue.Queue()

        self.session = Session(self)

        self.pvp = self.PVP_MODE_RE.match(api.game_server) is not None
        self.npc_attack_limit = 3 if not self.pvp else 5

        self.builder = BuildManager(self)
        self.tasks = {}
        self._cities = []

        self.events = self.builder.task(events.EventManager)

        self.alliance = self.builder.task(Alliance)
        self.favourites = self.builder.task(Favourites)
        self.item_manager = self.builder.task(item.Item)
        self.shop = self.builder.task(Shop)
        self.world = self.builder.task(World)

        self.scout_mail = ScoutMailHandler(self)
        self.war_mail = AttackMailHandler(self)


    def __del__(self):
        logger.debug('Clean up bot instance')
        self.disconnect()

    def disconnect(self):
        logger.info('Stop the task scheduler for this bot')
        self.scheduler.stop()

    def shutdown(self):
        self._closing = True
        self.session.end_time = time.time()
        try:
            self.session.save()
        except IOError:
            logger.warning('Error saving session')

    @property
    def userinfo(self):
        if not self.is_initialised and self._closing:
            raise BotException('userinfo unavailable and marked for shutdown')
        return self.data

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

        if self.api.player:
            if hasattr(settings, 'build_path') and \
                self.api.player.disable_global_build == False:

                self.tasks['build_path'] = settings.build_path

            if self.api.player.custom_build:
                self.tasks['custom'] = self.api.player.custom_build


        def inventory(event, *args, **kwargs):
            chat = self.builder.task(Chat)

            search_items = []
            for _search in args:
                for _id, _item in EmrossWar.ITEM.iteritems():
                    try:
                        if re.search(_search, _item.get('name'), re.IGNORECASE):
                            search_items.append(_id)
                    except re.error:
                        pass

            found = self.find_inventory_items(search_items)
            result = []
            for item_id, values in found.iteritems():
                name = EmrossWar.ITEM[str(item_id)].get('name')
                vals = [qty for uniqid, qty, sellable in values]
                result.append('{0}={1}'.format(name, sum(vals)))

            chat.send_message(', '.join(result))

        self.events.subscribe(self.INVENTORY_COMMAND, inventory)

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
            conqueror_id, conq_end, conq_name, _ = conquer

            if conqueror_id:
                parts.append(('conquered by', conq_name))
                f = self.human_friendly_time(conq_end - time.time())
                parts.append(('conquer ends', f))

            chat.send_message('{0}: {data}'.format(self.STATUS_COMMAND,
                data = ', '.join(['{0}={1}'.format(k,v) for k, v in parts])
            ))
        self.events.subscribe(self.STATUS_COMMAND, status)

        def uptime(event, *args, **kwargs):
            chat = self.builder.task(Chat)
            f = self.human_friendly_time(time.time() - self.session.start_time)
            chat.send_message('uptime: {0}'.format(f))
        self.events.subscribe(self.UPTIME_COMMAND, uptime)

        def wealth(event, *args, **kwargs):
            chat = self.builder.task(Chat)
            chat.send_message(self.total_wealth(*args, **kwargs))
        self.events.subscribe(self.WEALTH_COMMAND, wealth)

    def update(self):
        """
        Setup bot with player account data
        """
        logger.info('Updating player info')
        json = self.api.call(self.USERINFO_URL, pushid=self.api.pushid)

        userinfo = json['ret']['user']

        skip = set([city.id for city in self.cities])
        skip.update(settings.ignore_cities)
        cities = [city for city in userinfo['city'] if city['id'] not in skip]

        for city in cities:
            logger.debug(u'Adding "{0}" ({1}) to city list'.format(city['name'], city['id']))
            city = City(self, city['id'], city['name'], x=city['x'], y=city['y'])
            self._cities.append(city)

        if not self.is_initialised:
            self.is_initialised = True
            self.core_setup()

        for gift in userinfo['gift']:
            self.get_gift(gift)

        return userinfo

    def get_gift(self, gift):
        gid = int(gift['id'])
        try:
            gift_item = EmrossWar.ITEM[str(gid)]['name']
        except KeyError:
            gift_item = gid

        logger.info('Collecting gift "{0}"'.format(gift_item))
        return self.api.call(item.Item.ITEM_LIST, action='gift', id=gid)

    def find_target_for_army(self, city, cat=Favourites.DEVIL_ARMY):
        """
        Get next fav which is available for attack

        [18936, 165, 35, 1, 0]
        _, x, y, *, attacked
        """

        army, target = None, None

        try:
            for rating, threshold in settings.soldier_threshold:
                try:
                    army = city.create_army(threshold)
                except (InsufficientSoldiers, NoHeroesAvailable):
                    army, target = None, None
                    continue

                done = False
                favs = [e for e in self.favourites.favs[cat] if e.rating is rating]

                for t in favs:
                    if t.attack < self.npc_attack_limit:
                        target = t
                        done = True
                        break

                if done:
                    break

        except KeyError, e:
            pass

        if not army:
            raise InsufficientSoldiers

        if not target:
            if len(favs) == 0:
                raise NoTargetsFound, 'There are no DAs in the favs list for the selected army: %s' % army

            raise NoTargetsAvailable, 'No targets with less than %d attacks found!' % self.npc_attack_limit

        rating = (range(6, 0, -1)+range(7,9))[target.rating-1]
        logger.info('Target is %d* %d/%d with attack count %d' % (rating, target.y, target.x, target.attack))

        return target, army

    def scout_map(self, **kwargs):
        logger.info('Trying to find more targets to attack')

        try:
            last_scan = self.session.last_scan
        except AttributeError:
            last_scan = 0

        hours = kwargs.get('scouting_interval', 72)
        if time.time() < last_scan + hours*3600:
            logger.info('The world was scanned less than {0} hours ago'.format(hours))
        else:
            try:
                self.world.search(**kwargs)
                self.session.last_scan = time.time()
            except OutOfSpies as e:
                self.session.last_scan = 0
                logger.info(e)
            finally:
                self.session.save()

        try:
            logger.info('Look at scout reports to try to locate devil armies')
            self.scout_mail.process()
        except MailException:
            pass


    def is_attack_time(self):
        """
        Check if we should be farming at this time of day.
        Can't be farming 24/7 after all!
        """
        for timespan in settings.farming_hours:
            if timespan[0] <= time.localtime().tm_hour < timespan[1]:
                return True

        return False


    def _city_wealth(self, func=max, text='most'):
        city = func(self.cities, key = lambda c: c.resource_manager.get_amount_of(Resource.GOLD))
        logger.info('Chosen the city with the {0} {resource}, {city} ({amount})'.format(text,
            resource=EmrossWar.LANG.get('COIN', 'gold'),
            city=city.name, amount=city.resource_manager.get_amount_of(Resource.GOLD))
        )
        return city

    def richest_city(self):
        return self._city_wealth(max, 'most')

    def poorest_city(self):
        return self._city_wealth(min, 'least')

    def clean_war_reports(self):
        try:
            self.war_mail.process()
        except MailException:
            pass

    def clearout_inventory(self, city=None, use_items=False, sell_items=False, **kwargs):
        logger.info('Clear the item inventories')

        it = item.ItemType
        for itype in [it.WEAPON, it.ARMOR, it.RING, it.MOUNT, it.BOOK]:
            page = 1
            sale_list = []

            logger.info('Find items of type {0}'.format(itype))
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
                    logger.info('Last page of item type {0}'.format(itype))
                    break

            if sale_list:
                logger.info('Sell {0} item/s of type {1}'.format(len(sale_list), itype))
                city = city or self.poorest_city()

                for item_id in sale_list:
                    try:
                        json = self.item_manager.sell(city=city.id, id=item_id)
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
        it = item.ItemType

        # item type and the tab it is listed under
        item_types = {
            1: it.WEAPON,
            2: it.ARMOR,
            3: it.MOUNT,
            4: it.BOOK,
            5: it.BOOK,
            6: it.RING
        }
        search_items, result = dict(), dict()

        for id in items:
            try:
                i = EmrossWar.ITEM[str(id)]
                logger.debug('Searching for item {0}: "{1}"'.format(id, i.get('name')))
                item_type = item_types.get(i['type'], it.ITEM)
                search_items.setdefault(item_type, {})[int(id)] = False
            except KeyError:
                pass

        logger.debug(search_items)

        for item_type, search in search_items.iteritems():
            page = 1
            while False in search.values():
                json = self.item_manager.list(page=page, type=item_type)

                for _item in json['ret']['item']:
                    try:
                        if _item['item']['sid'] in search.keys():
                            res = [_item['item']['id'], _item['item']['num'], _item['sale']]
                            result.setdefault(_item['item']['sid'], []).append(res)
                            search[int(_item['item']['sid'])] = True
                    except KeyError:
                        pass

                page += 1
                if page > json['ret']['max']:
                    logger.info('Last page of item type {0}'.format(item_type))
                    break

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

            json = self.item_manager.sell(city = city.id, id = item_id, **kwargs)

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

        return getattr(settings, 'minimum_food', 0)

    @property
    def operators(self):
        ops = OPERATORS[:]
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
