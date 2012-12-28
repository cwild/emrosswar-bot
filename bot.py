import locale
import time

from emross import *
from emross.api import EmrossWar
from emross.exceptions import (EmrossWarApiException,
    InsufficientSoldiers,
    NoTargetsAvailable,
    NoTargetsFound)

from emross.utility.manager import BotManager
from emross.utility.player import Player

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



def run_bot(bot):
    """
    Steps necessary for the bot to "play" the game
    """
    logger.info('Starting bot')
    bot.session.start_time = time.time()
    logger.debug('Farming hours: %s' % settings.farming_hours)

    """
    We can make calls directly should we wish to:

    bot.api._call(settings.get_user_info, key=1, test=2)
    """

    while True:
        try:
            bot.update()

            try:
                bot.get_fav(EmrossWar.DEVIL_ARMY)

                logger.info('There are a total of %d DA which can be attacked a further %d times.' % (len(bot.fav[EmrossWar.DEVIL_ARMY]),
                            sum([bot.npc_attack_limit - x.attack for x in bot.fav[EmrossWar.DEVIL_ARMY]]) ))

                concurrent_attacks = []

                for city in bot.cities:
                    city.update()
                    city.recruit_hero()
                    city.replenish_food()

                    if bot.is_attack_time() is False:
                        continue

                    try:
                        """
                        How many (decent) soldiers are in this city?
                        """
                        logger.info('Getting soldiers')
                        city.get_soldiers()

                        logger.info('Getting available heroes')
                        city.get_available_heroes()


                        if hasattr(settings, 'prefer_closer') and settings.prefer_closer:
                            bot.sort_favs(city)

                        while True:
                            target, army = bot.find_target_for_army(city, EmrossWar.DEVIL_ARMY)

                            # choose hero which can lead this army
                            hero = city.choose_hero(sum(army.values()))
                            if not hero:
                                logger.info('No available heroes to command this army')

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

                            logger.info('Sending attack %d/%d' % (target.y, target.x))
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

                                    logger.info('Maximum number of concurrent attacks, %d, has been reached. Wait for longest current attack to return (%d seconds)' % (settings.concurrent_attack_limit, delay))

                                    concurrent_attacks[:] = []
                                    time.sleep(delay)
                            except AttributeError:
                                logger.critical('You need to set a concurrent attack limit.')


                    except AttributeError, e:
                        continue

                    except InsufficientSoldiers, e:
                        logger.info('%s has insufficient troops to launch an attack.' % city.name)
                        continue

                    except NoTargetsFound, e:
                        continue

                concurrent_attacks[:] = [e for e in concurrent_attacks if e > time.time()]

            except NoTargetsAvailable, e:
                logger.exception(e)
                logger.info('No targets available to attack.')



            """
            Now wait a while for things to return to their respective city
            """
            bot.scout_map()
            bot.clean_war_reports()

            if not bot.pvp:
                try:
                    bot.donator.make_donations(settings.donation_tech_preference)
                except AttributeError:
                    pass

                bot.clearout_inventory()

            logger.info('Total gold amongst all castles: %s' % (locale.format('%d', sum([c.get_gold_count()[0] for c in bot.cities]), True)))

            logger.info('Cycle finished, waiting for 5 mins to go again')
            time.sleep(5*MINUTE)

        except EmrossWarApiException, e:
            logger.exception(e)
            logger.info('Exception, sleeping for an hour')
            time.sleep(1*HOUR)



if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        argument_default=argparse.SUPPRESS,
        description='The EmrossWar Bot',
        epilog='%(prog)s --multi'
        )
    parser.add_argument('-m', '--multi', help='Multiple players at once!', action='store_true', default=False)
    parser.add_argument('-c', '--console', help='Interactive console', action='store_true', default=False)
    args = parser.parse_args()


    manager = BotManager(console=args.console)

    try:
        if not args.multi:
            player = Player(key=settings.api_key, server=settings.game_server, user_agent=settings.user_agent)
            manager.players.append(player)
        else:
            try:
                manager.players = settings.multi_bot
            except AttributeError:
                logger.critical('You must specify multiple bots in your settings file.')
                exit()

        manager.run(run_bot)

    except KeyboardInterrupt:
        for bot in manager.bots:
            bot.session.end_time = time.time()
            try:
                bot.session.save()
            except IOError:
                logger.warning('Error saving session')

        logger.info('Exiting')
