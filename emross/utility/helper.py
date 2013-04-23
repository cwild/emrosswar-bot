from __future__ import division

import logging
import math
import re
import time
import Queue
import sys
sys.path.extend(['lib/urllib3/'])

from lib import kronos
from lib.session import Session


from emross.alliance import Donator
from emross.api import EmrossWar
from emross.chat import Chat
from emross.city import City
from emross.exceptions import *
from emross.favourites import Favourites
from emross.gift import GiftCollector
from emross.item import inventory, item
from emross.lottery import AutoLottery
from emross.mail import AttackMailHandler, ScoutMailHandler, MailException
from emross.resources import Resource
from emross.shop import Shop
from emross.utility.builder import BuildManager
from emross.world import World

import settings

logger = logging.getLogger(__name__)

class EmrossWarBot:
    PVP_MODE_RE = re.compile('^p\d+\.')

    USERINFO_URL = 'game/get_userinfo_api.php'

    def __init__(self, api):
        self.blocked = False
        self.runnable = True

        self.api = api
        api.bot = self
        self.errors = Queue.Queue()

        self.session = Session(self)

        self.pvp = self.PVP_MODE_RE.match(api.game_server) is not None
        self.npc_attack_limit = 3 if not self.pvp else 5

        self.last_update = 0
        self.userinfo = None
        self.tasks = {}
        self.cities = []
        self.favourites = Favourites(self)
        self.item_manager = item.Item(self)
        self.shop = Shop(self)
        self.world = World(self)
        self.scout_mail = ScoutMailHandler(self)
        self.war_mail = AttackMailHandler(self)

        self.donator = Donator(self)
        try:
            self.donator.hall_donation_forced = settings.hall_donation_forced
        except AttributeError:
            pass

        self.scheduler = s = kronos.ThreadedScheduler()

        self.core_tasks = []
        self.core_setup()

        self.builder = BuildManager(self)
        self.tasks['core_tasks'] = s.add_interval_task(self.builder.process, "core task handler", 1, 1, kronos.method.sequential, [(self.core_tasks,), 'core'], None)

        if api.player:
            if api.player.disable_global_build == False:
                try:
                    self.tasks['build_path'] = s.add_interval_task(
                        self.builder.process,
                        "build path handler", 3, 1, kronos.method.sequential,
                        [settings.build_path, 'build'], None)
                except AttributeError:
                    pass

            if api.player.custom_build:
                self.tasks['custom'] = s.add_interval_task(
                    self.builder.process,
                    "custom build path handler", 1, 1, kronos.method.sequential,
                    [api.player.custom_build, 'custom'], None)

    def __del__(self):
        logger.debug('Clean up bot instance')
        self.disconnect()

    def disconnect(self):
        logger.info('Stop the task scheduler for this bot')
        self.scheduler.stop()

    def core_setup(self):
        """
        Setup our core tasks. These run in a separate thread.
        """
        self.core_tasks.append((Chat,))
        self.core_tasks.append((AutoLottery,))
        self.core_tasks.append((GiftCollector,))

    def update(self):
        """
        Setup bot with player account data
        """
        logger.info('Updating player info')
        json = self.api.call(self.USERINFO_URL, pushid=self.api.pushid)

        self.userinfo = userinfo = json['ret']['user']
        self.last_update = time.time()

        skip = set([city.id for city in self.cities])
        skip.update(settings.ignore_cities)
        cities = [city for city in userinfo['city'] if city['id'] not in skip]

        for city in cities:
            logger.debug('Adding "{0}" ({1}) to city list'.format(city['name'], city['id']))
            city = City(self, city['id'], city['name'], x=city['x'], y=city['y'])
            self.cities.append(city)

        for gift in userinfo['gift']:
            self.get_gift(gift)


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
                    army = city.create_army(threshold, False)
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

    def scout_map(self):
        logger.info('Trying to find more targets to attack')

        if not len(settings.farming_hours):
            logger.info('There are no times of day set to farm. No point scouting the map.')
            return

        try:
            last_scan = self.session.last_scan
        except AttributeError:
            last_scan = 0

        if time.time() < last_scan + (3 * 86400):
            logger.info('The world was scanned less than 3 days ago')
        else:
            try:
                self.world.search(settings.scout_devil_army_types)
                self.session.last_scan = time.time()
            except OutOfSpies, e:
                self.session.last_scan = 0
                logger.info(e)
                try:
                    logger.debug(self.session.map_coords)
                except AttributeError:
                    pass
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

    def clearout_inventory(self):
        logger.info('Clear the item inventories')

        it = item.ItemType
        for itype in [it.WEAPON, it.ARMOR, it.RING, it.MOUNT, it.BOOK]:
            page = 1
            sale_list = []

            logger.info('Find items of type %d' % itype)
            while True:
                json = self.item_manager.list(page = page, type = itype)

                for _item in json['ret']['item']:
                    try:
                        if item.ITEMS[_item['item']['sid']]['rank'] < item.ItemRank.RARE:
                            sale_list.append(_item['item']['id'])
                    except KeyError:
                        pass


                page += 1
                if page > json['ret']['max']:
                    logger.info('Last page of item type %d' % itype)
                    break

            if sale_list:
                logger.info('Sell %d item/s of type %d' % (len(sale_list), itype))
                city = self.poorest_city()

                for item_id in sale_list:
                    try:
                        json = self.item_manager.sell(city = city.id, id = item_id)
                        city.resource_manager.set_amount_of(Resource.GOLD, json['ret']['gold'])
                    except (KeyError, TypeError):
                        pass

                sale_list[:] = []

    def find_inventory_item(self, search_item):
        result = []
        it = item.ItemType

        item_id, item_type, item_rank = search_item

        if item_type not in [it.WEAPON, it.ARMOR, it.RING, it.MOUNT, it.BOOK]:
            item_type = it.ITEM

        page = 1
        found = False
        while not found:
            json = self.item_manager.list(page=page, type=item_type)

            for _item in json['ret']['item']:
                try:
                    if _item['item']['sid'] == item_id:
                        result.append([_item['item']['id'], _item['item']['num'], _item['sale']])
                        found = True
                    elif found:
                        logger.debug('We have found all of these items.')
                        break
                except KeyError:
                    pass

            page += 1
            if page > json['ret']['max']:
                logger.info('Last page of item type %d' % item_type)
                break

        return result


    def find_gold_for_city(self, city, gold, unbrick=False):
        """
        Given a city, try to find any items we have that we can sell for gold.
        """
        sellable_items = []

        total_amount = lambda: sum([qty*price for id, qty, price in sellable_items])

        if total_amount() < gold and unbrick:
            sellable_items.extend(self.find_inventory_item(inventory.GOLD_BRICK))
            sellable_items.extend(self.find_inventory_item(inventory.GOLD_BULLION))

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
