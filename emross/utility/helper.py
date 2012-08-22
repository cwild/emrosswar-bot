import sys
sys.path.extend(['lib/urllib3/'])


from lib import kronos
from lib.session import Session

from emross.item import item

import time
import math

import logging
logger = logging.getLogger(__name__)


from emross.alliance import Donator
from emross.api import EmrossWar
from emross.chat import Chat
from emross.exceptions import *
from emross.mail import *
from emross.world import OutOfSpies, World

import settings


class Unbuffered:
    def __init__(self, stream):
        self.stream = stream
    def write(self, data):
        self.stream.write(data)
        data = data.strip()
        if len(data):
            logging.info('CLI: %s' % data)
        self.stream.flush()
    def __getattr__(self, attr):
        return getattr(self.stream, attr)

sys.stdout = Unbuffered(sys.stdout)


class EmrossWarBot:
    def __init__(self, api):
        self.api = api

        self.scheduler = s = kronos.ThreadedScheduler()

        self.last_update = 0
        self.userinfo = None
        self.tasks = {}
        self.cities = []
        self.fav = {}
        self.scout_mail = ScoutMailHandler(api)
        self.war_mail = AttackMailHandler(api)
        Session.PATH = settings.session_path
        self.session = Session.load()
        self.donator = Donator(self)
        try:
            self.donator.hall_donation_forced = settings.hall_donation_forced
        except AttributeError:
            pass

        self.chatter = Chat(self)
        self.tasks['chat'] = s.add_interval_task(self.chatter.check, "chat handler", 3, 6, kronos.method.threaded, [], None)

        s.start()


    def update(self):
        """
        Setup bot with player account data
        """
        json = self.api.call(settings.get_user_info, pushid=settings.pushid, **{'_l':'en'} )

        if json['code'] == 2:
            self.last_update = 0
            raise EmrossWarApiException, 'Error during load'


        if json['code'] in [EmrossWar.PVP_ELIMINATED]:
            print 'You have been eliminated from PvP!'
            exit()

        self.userinfo = userinfo = json['ret']['user']
        self.last_update = time.time()

        if len(self.cities) == 0:
            cities = [city for city in userinfo['city'] if city['id'] not in settings.ignore_cities]

            for city in cities:
                city = City(self, city['id'], city['name'], x = city['x'], y = city['y'])
                self.cities.append(city)


        gifts = userinfo['gift']

        for gift in gifts:
            self.get_gift(gift)


    def get_gift(self, gift):
        logger.info('Collecting gift %d' % gift['id'])
        json = self.api.call(settings.get_goods, action='gift', id=gift['id'], _l='en')


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
        self.fav[cat].sort(key=lambda fav: math.sqrt((fav.x - nx)**2 + (fav.y - ny)**2))


    def clear_favs(self):
        for f in self.fav[EmrossWar.DEVIL_ARMY]:
            print 'Deleting fav %d' % f.id
            self.api.call(settings.api_fav, act='delfavnpc', fid=f.id)


    def find_target_for_army(self, city, cat = EmrossWar.DEVIL_ARMY):
        """
        Get next fav which is available for attack

        [18936, 165, 35, 1, 0]
        _, x, y, *, attacked
        """

        target = None
        army = None

        try:
            for rating, threshold in settings.soldier_threshold:
                try:
                    army = city.create_army(threshold, False)
                except InsufficientSoldiers:
                    continue

                done = False
                favs = [e for e in self.fav[cat] if e.rating is rating]

                for t in favs:
                    if t.attack < settings.npc_attack_limit:
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
            raise NoTargetsAvailable, 'No targets with less than %d attacks found!' % settings.npc_attack_limit

        rating = range(6, 0, -1)[target.rating-1]
        print 'Target is %d* %d/%d with attack count %d' % (rating, target.y, target.x, target.attack)

        return target, army




    def scout_map(self):
        print 'Trying to find more targets to attack'

        if not len(settings.farming_hours):
            print 'There are no times of day set to farm. No point scouting the map.'
            return

        try:
            last_scan = self.session.last_scan
        except AttributeError:
            last_scan = 0

        if time.time() < last_scan + (3 * 86400):
            print 'The world was scanned less than 3 days ago'
        else:
            try:
                world = World(self)
                world.search(settings.scout_devil_army_types)
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
            print 'Look at scout reports to try to locate devil armies'
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
        city = max(self.cities, key = lambda c: c.get_gold_count()[0])
        print 'Chosen the city with the most gold, %s (%d)' % (city.name, city.get_gold_count()[0])
        return city

    def poorest_city(self):
        city = min(self.cities, key = lambda c: c.get_gold_count()[0])
        print 'Chosen the city with the least gold, %s (%d)' % (city.name, city.get_gold_count()[0])
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

            city = self.poorest_city()
            print 'Sell %d item/s of type %d' % (len(sale_list), itype)

            for item_id in sale_list:
                json = item_manager.sell(city = city.id, id = item_id)
                try:
                    city.data[2] = json['ret']['gold']
                except KeyError:
                    pass

            sale_list[:] = []


class City:
    GET_CITY_INFO = 'game/get_cityinfo_api.php'

    def __init__(self, bot, id, name, x, y):
        self.bot = bot
        self.id = id
        self.name = name.encode('utf-8')
        self.x = x
        self.y = y
        self.data = None

        self.heroes = []
        self.soldiers = []

        self.market = None
        self.next_hero_recruit = time.time()


    def update(self):
        """Get castle info"""

        """
        {"code":0,"ret":{"city":
            [
                12,210,          # Free land
                3736203,5766504, # Gold
                4508554,5766504, # Food
                1110460,5766504, # Wood
                2275066,5766504, # Iron
                11433,12232,     # Population

                14, # Sawmill
                12, # Iron
                5,  # Gold
                29, # Farm
                20, # House
                25, # Barracks
                22, # Uni
                21, # Arena
                10, # Storage
                20, # Wall
                18, # Facility Center
                [{"id":11659,"itemid":166,"secs":532417}],0],"grade":53,"money":40}}
        """

        json = self.bot.api.call(self.GET_CITY_INFO, city = self.id)
        self.data = json['ret']['city']


    def get_countdown_info(self):
        """
        Get info about countdown tasks for this city
        """
        pass


    def get_data(self, i):
        if self.data is None:
            self.update()

        return self.data[i]

    def get_gold_count(self):
        return (self.get_data(2), self.get_data(3))


    def get_food_count(self):
        return (self.get_data(4), self.get_data(5))


    def replenish_food(self, amount = None):
        if not self.market:
            self.get_local_market_info()

        if not amount:
            food = self.get_food_count()
            amount = food[1] - food[0]

        buy_gold = int(math.ceil(self.market.get_gold_to_food_rate() * amount))

        available_gold = self.get_gold_count()[0]

        if buy_gold > available_gold:
            buy_gold = available_gold

        if buy_gold and buy_gold > 0:
            print 'trying with %d gold' % buy_gold
            json = self.bot.api.call(settings.local_market, city = self.id, reso_put='giveput', g2f=buy_gold)



    def get_local_market_info(self):
        json = self.bot.api.call(settings.local_market, city = self.id)
        self.market = Market(json['ret'])



    def get_soldiers(self):
        json = self.bot.api.call(settings.get_soldiers, city = self.id)
        try:
            self.soldiers = json['ret']['soldiers']
        except TypeError:
            pass

    def create_army(self, threshold, deduct = True):
        """
        Return a dict of the various soldiers to include in this army
        """

        army = {}

        for soldier, qty in threshold.iteritems():
            """
            If there are enough of a given soldier to send
            then add them to the army
            """
            try:
                if (max([h.get_capacity() for h in self.heroes]) < qty):
                    continue

                soldiers = [s for s in self.soldiers if s[0] == soldier][0]

                if soldiers[1] >= qty:
                    army['soldier_num%d' % soldier] = qty

                    """
                    Update soldier cache
                    """
                    if deduct:
                        soldiers[1] -= qty

                    break
            except (IndexError, ValueError):
                pass


        if not army:
            raise InsufficientSoldiers, 'No soldiers were added to the army'

        return army


    def get_army_count(self):
        """
        Calculate the number of armies this castle has
        """
        count = 0

        for soldier, qty in settings.soldier_threshold.iteritems():
            try:
                soldiers = [s for s in self.soldiers if s[0] == soldier][0]
                count += int(math.floor(soldiers[1] / qty))
            except (IndexError, ValueError, ZeroDivisionError):
                pass

        return count


    def get_available_heroes(self):
        """
        Find the available heroes for this city
        """

        """
        {"hero":[
            {"id":13668,"gid":70,"p":56,"i":24,"c1":23,"f":50,"g":12,"c2":906,"fy":0,"s":0,"e":16,"w":3,"tw":3,"tl":0,"ex":141056,"te":257100,"np":0,"ni":0,"nc1":0,"nc2":150,"ns":0,"ncd":0,"pr":36000},
            {"id":12608,"gid":59,"p":36,"i":70,"c1":40,"f":50,"g":14,"c2":859,"fy":0,"s":0,"e":16,"w":1,"tw":12,"tl":2,"ex":405312,"te":1244364,"np":0,"ni":0,"nc1":0,"nc2":0,"ns":0,"ncd":0,"pr":42000},
            {"id":13048,"gid":83,"p":65,"i":20,"c1":41,"f":50,"g":13,"c2":819,"fy":0,"s":0,"e":16,"w":1,"tw":9,"tl":1,"ex":40897,"te":565620,"np":35,"ni":16,"nc1":35,"nc2":432,"ns":0,"ncd":0,"pr":39000},
            {"id":12939,"gid":60,"p":61,"i":21,"c1":26,"f":50,"g":13,"c2":836,"fy":0,"s":0,"e":16,"w":2,"tw":8,"tl":4,"ex":269883,"te":565620,"np":0,"ni":0,"nc1":0,"nc2":0,"ns":0,"ncd":0,"pr":39000},
            {"id":13460,"gid":22,"p":92,"i":24,"c1":46,"f":50,"g":13,"c2":987,"fy":0,"s":0,"e":16,"w":6,"tw":6,"tl":0,"ex":23574,"te":565620,"np":55,"ni":23,"nc1":45,"nc2":744,"ns":0,"ncd":0,"pr":39000},
            {"id":11969,"gid":10,"p":102,"i":22,"c1":46,"f":60,"g":15,"c2":1111,"fy":0,"s":0,"e":16,"w":2,"tw":69,"tl":9,"ex":1194745,"te":2737601,"np":100,"ni":25,"nc1":52,"nc2":1024,"ns":0,"ncd":0,"pr":45000},
            {"id":13616,"gid":72,"p":78,"i":17,"c1":23,"f":50,"g":12,"c2":933,"fy":0,"s":0,"e":16,"w":4,"tw":5,"tl":1,"ex":56470,"te":257100,"np":0,"ni":0,"nc1":0,"nc2":150,"ns":0,"ncd":0,"pr":36000}
            ]
        }
        """
        json = self.bot.api.call(settings.get_heroes, city=self.id, action='gen_list', extra=1)
        self.heroes[:] = []

        heroes = sorted(json['ret']['hero'], key = lambda val: (val['g'], val['ex']))

        for data in heroes:
            #print 'Level %d, Exp %d' % (data['g'], data['ex'])
            self.heroes.append(Hero(data))


    def choose_hero(self, capacity = None):
        """
        Which hero should we use?
        """

        hero = None

        try:
            if capacity:
                for h in self.heroes:
                    if h.get_capacity() >= capacity:
                        hero = h
                        break

                self.heroes.remove(hero)
            else:
                hero = self.heroes.pop(0)
        except ValueError:
            pass

        return hero


    def action_confirm(self, params):
        """
        We need to confirm that we wish to perform this action.

        Shows the cost of performing the action both in resources and time

        city=12553&action=do_war&attack_type=7&gen=22&area=110&area_x=258&soldier_num15=600&_l=en
        """

        if not hasattr(settings, 'TOO_OFTEN_WARNING'):
            raise EmrossWarException, 'You need to set the API TOO_OFTEN_WARNING code in your settings file'

        if not params['gen']:
            raise ValueError, 'Need to send a hero to lead the army'

        json = self.bot.api.call(settings.action_confirm, sleep=(5,8), city=self.id, **params)

        """ Returns the cost of war """
        """
        {"code":0,"ret":{"carry":820800,"cost_food":108000,"cost_wood":0,"cost_iron":0,"cost_gold":0,"distance":6720,"travel_sec":120}}
        """

        return json['ret']

    def action_do(self, params):
        """
        city=12553&action=war_task&attack_type=7&gen=22&area=110&area_x=258&soldier_num15=600

        carry=820800&cost_food=108000&cost_wood=0&cost_iron=0&cost_gold=0&distance=6720&travel_sec=120
        """

        try:
            if params['cost_food'] > self.get_data(4):
                self.replenish_food(params['cost_food'] - self.get_data(4))
        except KeyError, e:
            logger.exception(e)
            logger.info(params)

        json = self.bot.api.call(settings.action_do, sleep=(1,3), city=self.id, **params)

        if json['code'] == settings.TOO_OFTEN_WARNING:
            raise EmrossWarApiException, 'We have been rate limited. Come back later.'

        soldiers = [(k.replace('soldier_num', ''), v) for k, v in params.iteritems() if k.startswith('soldier_num')]
        for k, v in soldiers:
            i = int(k) - 1
            self.soldiers[i][1] -= v



    def recruit_hero(self):
        if not settings.enable_recruit:
            return

        if time.time() < self.next_hero_recruit:
            return

        print 'Check for heroes at the bar in "%s"' % self.name
        json = self.bot.api.call(settings.hero_conscribe, city=self.id)


        if 'refresh' in json['ret']:
            print 'We have to wait before we can do this. Timer: %d' % json['ret']['refresh']
            self.next_hero_recruit = time.time() + int(json['ret']['refresh'])
        else:
            print 'Try buying a drink'
            json = self.bot.api.call(settings.hero_conscribe, city=self.id, action='pub_process')

            if json['code'] == EmrossWar.REACHED_HERO_LIMIT:
                print 'Hero limit has been reached for this castle.'
                return


            if json['code'] == EmrossWar.INSUFFICIENT_GOLD:
                print 'Insufficient gold to buy a drink!'
                return
            else:
                self.next_hero_recruit = time.time() + int(json['ret']['refresh'])


            if 'hero' in json['ret'] and json['ret']['hero']['gid'] in settings.recruit_heroes:
                print 'Found a hero we are looking for: %d' % json['ret']['hero']['gid']
                json = self.bot.api.call(settings.hero_conscribe, city=self.id, action='hire_process')

                if json['code'] == EmrossWar.SUCCESS:
                    print 'Hero recruited!'
                else:
                    print 'Could not recruit hero.'


    def check_war_room(self):
        json = self.bot.api.call(settings.action_confirm, act='warinfo', city=self.id)


class Hero:
    def __init__(self, data = {}):
        self.data = data

    def update(self, data):
        self.data = data

    def get_status(self):
        pass

    def get_capacity(self):
        return self.data['c2']


class Fav:
    def __init__(self, x = 0, y = 0, attack = 0):
        self.x = x
        self.y = y
        self.attack = attack


class Market:
    def __init__(self, data):
        """
        Setup local market info
        {"code":0,"ret":{"g2w":0.06,"g2f":0.13,"g2i":0.1,"w2g":17,"f2g":80,"i2g":11}}
        """
        self.data = data

    def get_gold_to_food_rate(self):
        return self.data['g2f']

class InsufficientSoldiers(BotException):
    def __init__(self, troop_count = 0):
        self.troop_count = troop_count
