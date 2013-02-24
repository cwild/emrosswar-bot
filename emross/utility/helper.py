import sys
sys.path.extend(['lib/urllib3/'])


from lib import kronos
from lib.session import Session

from emross.item import item
from emross.resources import Resource
from emross.shop import Shop

import math
import re
import time
import Queue

import logging
logger = logging.getLogger(__name__)


from emross.alliance import Donator
from emross.api import EmrossWar
from emross.chat import Chat
from emross.city import City
from emross.exceptions import *
from emross.lottery import AutoLottery
from emross.mail import AttackMailHandler, ScoutMailHandler, MailException
from emross.utility.builder import BuildManager
from emross.world import World

import settings

class EmrossWarBot:
    PVP_MODE_RE = re.compile('^p\d+\.')

    USERINFO_URL = 'game/get_userinfo_api.php'

    def __init__(self, api):
        self.api = api
        api.bot = self
        self.errors = Queue.Queue()

        self.session = Session.load(api.api_key)

        self.pvp = self.__class__.PVP_MODE_RE.match(api.game_server) is not None
        self.npc_attack_limit = 3 if not self.pvp else 5

        self.last_update = 0
        self.userinfo = None
        self.tasks = {}
        self.cities = []
        self.fav = {}
        self.shop = Shop(self)
        self.world = World(self)
        self.scout_mail = ScoutMailHandler(api)
        self.war_mail = AttackMailHandler(api)

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

        try:
            self.tasks['build_path'] = s.add_interval_task(self.builder.process, "build path handler", 3, 1, kronos.method.sequential, [settings.build_path, 'build'], None)
        except AttributeError:
            pass


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
            logger.debug('Adding "%s" to city list' % city['name'])
            city = City(self, city['id'], city['name'], x = city['x'], y = city['y'])
            self.cities.append(city)


        for gift in userinfo['gift']:
            self.get_gift(gift)


    def get_gift(self, gift):
        gid = int(gift['id'])
        logger.info('Collecting gift %d' % gid)
        json = self.api.call('game/goods_api.php', action='gift', id=gid, _l='en')


    def get_fav(self, cat = EmrossWar.DEVIL_ARMY):
        json = self.api.call(settings.api_fav, act = 'getfavnpc', cat = cat)

        favs = json['ret']['favs']

        self.fav[cat] = []
        for da in favs:
            #[[14785,115,248,1,3]
            # Seems that x,y are back to front
            fav = Fav(y = da[1], x = da[2], attack = da[4])
            fav.id = da[0]
            fav.rating = da[3]
            self.fav[cat].append(fav)


    def sort_favs(self, city, cat = EmrossWar.DEVIL_ARMY):
        """
        Sort favs based on proximity from city (ascending distance)
        """
        nx, ny = city.y, city.x # Backwards..?
        max = self.world.map_size()
        self.fav[cat].sort(key=lambda fav: math.sqrt( min(abs(fav.x-nx), max[0]-abs(fav.x-nx))**2  + min( abs(fav.y-ny), max[1]-abs(fav.y-ny) )**2) )


    def clear_favs(self):
        for f in self.fav[EmrossWar.DEVIL_ARMY]:
            logger.info('Deleting fav %d' % f.id)
            self.api.call(settings.api_fav, act='delfavnpc', fid=f.id)


    def find_target_for_army(self, city, cat = EmrossWar.DEVIL_ARMY):
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
                except InsufficientSoldiers:
                    army, target = None, None
                    continue

                done = False
                favs = [e for e in self.fav[cat] if e.rating is rating]

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


    def richest_city(self):
        city = max(self.cities, key = lambda c: c.resource_manager.get_amount_of(Resource.GOLD))
        logger.info('Chosen the city with the most gold, %s (%d)' % (city.name, city.resource_manager.get_amount_of(Resource.GOLD)))
        return city

    def poorest_city(self):
        city = min(self.cities, key = lambda c: c.resource_manager.get_amount_of(Resource.GOLD))
        logger.info('Chosen the city with the least gold, %s (%d)' % (city.name, city.resource_manager.get_amount_of(Resource.GOLD)))
        return city


    def clean_war_reports(self):
        try:
            self.war_mail.process()
        except MailException:
            pass



    def clearout_inventory(self):
        logger.info('Clear the item inventories')

        item_manager = item.Item(self)
        it = item.ItemType
        for itype in [it.WEAPON, it.ARMOR, it.RING, it.MOUNT, it.BOOK]:
            page = 1
            sale_list = []

            logger.info('Find items of type %d' % itype)
            while True:
                json = item_manager.list(page = page, type = itype)

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
                        json = item_manager.sell(city = city.id, id = item_id)
                        city.resource_manager.set_amount_of(Resource.GOLD, json['ret']['gold'])
                    except (KeyError, TypeError):
                        pass

                sale_list[:] = []

    def find_inventory_item(self, search_item):
        result = []

        item_manager = item.Item(self)
        it = item.ItemType

        item_id, item_type, item_rank = search_item

        if item_type not in [it.WEAPON, it.ARMOR, it.RING, it.MOUNT, it.BOOK]:
            item_type = it.ITEM

        page = 1
        found = False
        while not found:
            json = item_manager.list(page = page, type = item_type)

            for _item in json['ret']['item']:
                try:
                    if _item['item']['sid'] == item_id:
                        result.append([_item['item']['id'], _item['item']['num']])
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


class Fav:
    def __init__(self, x = 0, y = 0, attack = 0):
        self.x = x
        self.y = y
        self.attack = attack
