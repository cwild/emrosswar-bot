import math
import time

from emross.api import EmrossWar
from emross.arena.hero import Hero
from emross.exceptions import InsufficientSoldiers
import settings

class City:
    GET_CITY_INFO = 'game/get_cityinfo_api.php'
    GET_COUNTDOWN_INFO = 'game/get_cdinfo_api.php'

    def __init__(self, bot, id, name, x, y):
        self.bot = bot
        self.id = id
        self.name = name.encode('utf-8')
        self.x = x
        self.y = y
        self._data = None

        self.heroes = []
        self.soldiers = []

        self.market = None
        self.next_hero_recruit = time.time()


    @property
    def data(self):
        if self._data is None:
            self.update()
        return self._data


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
        self._data = json['ret']['city']


    def get_countdown_info(self):
        """
        Get info about countdown tasks for this city
        """
        return self.bot.api.call(self.GET_COUNTDOWN_INFO, city=self.id)


    def get_data(self, i):
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
                if (max([h.data.get(Hero.COMMAND) for h in self.heroes]) < qty):
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


    def get_available_heroes(self, extra=1):
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
        json = self.bot.api.call(settings.get_heroes, city=self.id, action='gen_list', extra=extra)
        self.heroes[:] = []

        heroes = sorted(json['ret']['hero'], key = lambda val: (Hero.LEVEL, Hero.EXPERIENCE))

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
                    if h.data.get(Hero.COMMAND) >= capacity:
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
            soldier = [s for s in self.solders if i == s[0]][0]
            soldier[1] -= v



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


class Market:
    def __init__(self, data):
        """
        Setup local market info
        {"code":0,"ret":{"g2w":0.06,"g2f":0.13,"g2i":0.1,"w2g":17,"f2g":80,"i2g":11}}
        """
        self.data = data

    def get_gold_to_food_rate(self):
        return self.data['g2f']
