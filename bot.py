#!/usr/bin/python

import locale
import time
from emross import *
from emross.utility.helper import *

import logging
logger = logging.getLogger(__name__)

import settings

logging.basicConfig(level=settings.log_level,
                    format='%(asctime)s, %(name)s (%(levelname)s): %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename=settings.logfile, filemode='a')



locale.setlocale(locale.LC_ALL, '')

SECOND = 1
MINUTE = 60 * SECOND
HOUR   = 60 * MINUTE

api = EmrossWarApi(settings.api_key, settings.game_server, settings.user_agent)
bot = EmrossWarBot(api)


def main():
    """
    Steps necessary for the bot to "play" the game
    """
    print 'Starting bot'
    bot.session.start_time = time.time()

    """
    We can make calls directly should we wish to:

    bot.api._call(settings.get_user_info, key=1, test=2)
    """

    while True:
        try:
            print 'Updating player info'
            bot.update()

            try:
                bot.get_fav(EmrossWar.DEVIL_ARMY)
                #bot.clear_favs()

                print 'There are a total of %d DA which can be attacked a further %d times.' % (len(bot.fav[2]),
                            sum([settings.npc_attack_limit - x.attack for x in bot.fav[2]]) )

                concurrent_attacks = []

                for city in bot.cities:
                    print 'Updating city %s' % city.name
                    city.update()

                    city.recruit_hero()

                    print 'Replenishing food'
                    city.replenish_food()

                    if bot.is_attack_time() is False:
                        continue

                    try:
                        """
                        How many (decent) soldiers are in this city?
                        """
                        print 'Getting soldiers'
                        city.get_soldiers()

                        print 'Getting available heroes'
                        city.get_available_heroes()


                        if hasattr(settings, 'prefer_closer') and settings.prefer_closer:
                            bot.sort_favs(city)

                        while True:
                            target, army = bot.find_target_for_army(city, EmrossWar.DEVIL_ARMY)

                            # choose hero which can lead this army
                            hero = city.choose_hero(sum(army.values()))
                            if not hero:
                                print 'No available heroes to command this army'

                            # send troops to attack
                            params = {
                                'action': 'do_war',
                                'attack_type': EmrossWar.ACTION_ATTACK,
                                'gen': hero.data['gid'],
                                'area': target.y,
                                'area_x': target.x
                            }

                            params.update(army)

                            cost = city.action_confirm(params)
                            params.update(cost)

                            print 'Sending attack %d/%d' % (target.y, target.x)
                            city.action_do(params)

                            try:
                                roundtrip = params['travel_sec'] * 2
                                concurrent_attacks.append(time.time() + roundtrip)
                            except KeyError, e:
                                logger.exception(e)
                                logger.debug(params)
                                continue

                            """
                            Update cache as targets are only updated once per city rather than per hero
                            """
                            target.attack += 1

                            try:
                                if len(concurrent_attacks) == settings.concurrent_attack_limit:
                                    delay = max(concurrent_attacks) - time.time()

                                    print 'Maximum number of concurrent attacks, %d, has been reached. Wait for longest current attack to return (%d seconds)' % (settings.concurrent_attack_limit, delay)

                                    concurrent_attacks[:] = []
                                    time.sleep(delay)
                            except AttributeError:
                                logger.critical('You need to set a concurrent attack limit.')


                    except AttributeError, e:
                        continue

                    except InsufficientSoldiers, e:
                        print '%s has insufficient troops to launch an attack.' % city.name
                        continue

                concurrent_attacks[:] = [e for e in concurrent_attacks if e > time.time()]

            except NoTargetsAvailable, e:
                logger.exception(e)
                print 'No targets available to attack.'

            except NoTargetsFound, e:
                logger.exception(e)
                print 'No targets found'

                for city in bot.cities:
                    city.update()
                    city.recruit_hero()
                    city.replenish_food()

                bot.scout_map()

                bot.get_fav(EmrossWar.DEVIL_ARMY)

                ratings = dict(settings.soldier_threshold)
                if len([f for f in bot.fav[EmrossWar.DEVIL_ARMY] if f.attack < settings.npc_attack_limit and f.rating in ratings]):
                    print 'We have some more Devil Armies to attack!'
                else:
                    print 'None found, sleep for 30 minutes'
                    time.sleep(30*MINUTE)

                continue



            """
            Now wait a while for things to return to their respective city
            """
            bot.scout_map()
            bot.clean_war_reports()

            try:
                bot.donator.make_donations(settings.donation_tech_preference)
            except AttributeError:
                pass

            print 'Total gold amongst all castles: %s' % (locale.format('%d', sum([c.get_gold_count()[0] for c in bot.cities]), True))

            print 'Cycle finished, waiting for 5 mins to go again'
            time.sleep(5*MINUTE)

        except EmrossWarApiException, e:
            print e
            print 'Exception, sleeping for an hour'
            time.sleep(1*HOUR)



if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        bot.session.end_time = time.time()
        bot.session.save()
        print '\nExiting'