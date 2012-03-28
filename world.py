import time

import settings
from emross import *

import logging
logger = logging.getLogger('emross-bot')

class WorldException(Exception): pass

class OutOfSpies(WorldException): pass

class World:
    def __init__(self, api, bot):
        self.api = api
        self.bot = bot
        self.cities = bot.cities
        self.favs = bot.fav[EmrossWar.DEVIL_ARMY]


    def scout(self, city, x, y):
        """
        Scout the co-ord
        """

        """ These x,y params seem backwards, d'oh!"""
        params = {
            'city': city,
            'action': 'do_war',
            'attack_type': EmrossWar.ATTACK_TYPE_SCOUT,
            'tai_num': 1,
            'area': x,
            'area_x': y
        }

        json = self.api.call(settings.action_confirm, **params)

        params.update(json['ret'])
        json = self.api.call(settings.action_do, **params)

        return json['code'] == EmrossWar.SUCCESS


    def get_city_with_spies(self):
        """Choose a city with spies"""
        choice = None
        for city in self.cities:
            city.get_soldiers()
            try:
                if city.soldiers[Soldier.SPY-1][1]:
                    if not choice or city.soldiers[Soldier.SPY-1][1] > choice.soldiers[Soldier.SPY-1][1]:
                        choice = city
            except IndexError:
                pass

        if choice:
            print 'Sending spies from %s' % choice.name
            return choice

        print 'Unable to locate any available spies, sleeping for 5 mins.'
        time.sleep(300)


    def search(self, targets = []):
        if not targets:
            print 'No targets to scout'
            return

        city = self.get_city_with_spies()
        if not city:
            print 'No cities found with spies.'
            return

        try:
            x, y, nx, ny = self.bot.session.map_coords
        except AttributeError:
            x, y, nx, ny = 1, 1, 1, 1

        page = self.get_page(x, y)

        nx = page['xleft']
        ny = page['yup']

        spies = 0

        while y < ny:
            x = 0

            while x < nx:
                self.bot.session.map_coords = (x, y, nx, ny)

                try:
                    for item in page['map']:
                        if item[2] in targets:
                            if not spies:
                                for tries in xrange(2):
                                    city.get_soldiers()
                                    spies = city.soldiers[Soldier.SPY-1][1]
                                    print 'Found %d spies in the city %s' % (spies, city.name)
                                    if not spies:
                                        if tries == 0:
                                            logger.info('Check the war room. Try to trigger spy count to update')
                                            city.check_war_room()
                                        else:
                                            raise OutOfSpies, 'No spies available at the moment'
                                    else:
                                         break


                            favs = [f for f in self.favs if f.x == item[1] and f.y == item[0]]
                            if favs:
                                print 'Already a fav, skipping'
                                continue

                            print 'Scouting [%d, %d]' % (item[0], item[1])
                            self.scout(city.id, item[0], item[1])
                            spies -= 1



                    if page['xright'] > x:
                        x = page['xright']
                        page = self.get_page(x, y)
                    else:
                        break

                except WorldException:
                    print 'Sleeping for 5 mins'
                    time.sleep(600)


            if page['ydown'] > y:
                y = page['ydown']
                page = self.get_page(x, y)
            else:
                try:
                    del self.bot.session.map_coords
                except AttributeError:
                    pass

                print 'Finished scouting map'
                break



    def get_page(self, x, y):
        print 'Get page x=%d y=%d' % (x,y)
        json = self.api.call(settings.world_map, x=x, y=y)

        if json['code'] != EmrossWar.SUCCESS:
            return

        return json['ret']
