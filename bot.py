import logging
import time

"""
If logging hasn't already been configured, setup our own from logging.conf files
"""
if len(logging.root.handlers) == 0:
    from ConfigParser import NoSectionError
    import logging.config

    try:
        logging.config.fileConfig('build/logging.conf')
    except NoSectionError:
        logging.config.fileConfig('logging.conf')


# Application settings, configurable
import settings

from emross.api import EmrossWar
from emross.exceptions import (EmrossWarApiException,
    InsufficientSoldiers,
    NoTargetsAvailable,
    NoTargetsFound)
from emross.favourites import Favourites

from emross.utility.manager import BotManager
from emross.utility.player import Player

try:
    import emross.handlers
    emross.handlers.handlers[settings.TOO_OFTEN_WARNING] = emross.handlers.VisitTooOftenHandler
except AttributeError:
    raise AttributeError('You need to set the API TOO_OFTEN_WARNING code in your settings file')


SECOND = 1
MINUTE = 60 * SECOND
HOUR   = 60 * MINUTE

logger = logging.getLogger(__name__)

def run_bot(bot):
    """
    Steps necessary for the bot to "play" the game
    """
    logger.info('Starting bot')
    bot.session.start_time = time.time()
    logger.debug('Farming hours: {0}'.format(getattr(settings, 'farming_hours', None)))
    bot.scheduler.should_start = True

    """
    We can make calls directly should we wish to:

    bot.api._call(settings.get_user_info, key=1, test=2)
    """

    while bot.runnable:
        try:
            bot.update()

            try:
                bot.favourites.get_favs(Favourites.DEVIL_ARMY)

                logger.info('There are a total of {num} {monster} which can be attacked a further {remain} times.'.format(\
                    num=len(bot.favourites.favs[Favourites.DEVIL_ARMY]),
                    monster=EmrossWar.LANG.get('MONSTER', 'NPCs'),
                    remain=sum([bot.npc_attack_limit - x.attack for x in bot.favourites.favs[Favourites.DEVIL_ARMY]])\
                ))

                concurrent_attacks = []

                for city in bot.cities:
                    # force city to update
                    city.expire()
                    city.replenish_food()

                    if bot.is_attack_time() is False:
                        continue

                    try:
                        """
                        How many (decent) soldiers are in this city?
                        """
                        city.barracks.get_soldiers()

                        logger.info('Getting available heroes')
                        city.get_available_heroes()


                        if getattr(settings, 'prefer_closer', False):
                            bot.favourites.sort_favs(city)

                        while True:
                            target, army = bot.find_target_for_army(city, Favourites.DEVIL_ARMY)

                            # choose hero which can lead this army
                            hero = city.choose_hero(sum(army.values()))
                            if not hero:
                                logger.info('No available heroes to command this army')
                                raise ValueError('Need to send a hero to lead the army')

                            logger.info('Sending attack %d/%d' % (target.y, target.x))

                            # send troops to attack
                            params = {
                                'action': 'do_war',
                                'attack_type': EmrossWar.ACTION_ATTACK,
                                'gen': hero.data['gid'],
                                'area': target.y,
                                'area_x': target.x
                            }
                            params.update(army)

                            json = city.barracks.confirm_and_do(params, sleep_confirm=(5,8), sleep_do=(1,3))

                            roundtrip = params.get('travel_sec', 0) * 2
                            concurrent_attacks.append(time.time() + roundtrip)

                            """
                            Update cache as targets are only updated once per city rather than per hero
                            """
                            if json['code'] == EmrossWar.SUCCESS:
                                target.attack += 1

                            try:
                                if len(concurrent_attacks) == settings.concurrent_attack_limit:
                                    delay = max(concurrent_attacks) - time.time()

                                    logger.info('Maximum number of concurrent attacks, %d, has been reached. Wait for longest current attack to return (%d seconds)' % (settings.concurrent_attack_limit, delay))

                                    concurrent_attacks[:] = []
                                    time.sleep(delay)
                            except AttributeError:
                                logger.critical('You need to set a concurrent attack limit.')


                    except AttributeError as e:
                        logger.exception(e)

                    except InsufficientSoldiers as e:
                        logger.info('%s has insufficient troops to launch an attack.' % city.name)
                        continue

                    except NoTargetsFound:
                        continue

                concurrent_attacks[:] = [e for e in concurrent_attacks if e > time.time()]

            except NoTargetsAvailable as e:
                logger.info('No targets available to attack.')



            """
            Now wait a while for things to return to their respective city
            """
            bot.scout_map()
            bot.clean_war_reports()

            if not bot.pvp:
                bot.clearout_inventory()

            logger.info(bot.total_wealth())

            logger.info('Cycle finished, waiting for 5 mins to go again')
            time.sleep(5*MINUTE)

        except EmrossWarApiException as e:
            logger.exception(e)
            logger.info('EmrossWarApiException, sleeping for 15 minutes')
            time.sleep(15*MINUTE)
        except Exception as e:
            logger.exception(e)
            logger.info('Exception, sleeping for an hour')
            time.sleep(1*HOUR)

    bot.disconnect()

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

else:
    import threading
    def test_bot():
        manager = BotManager()
        try:
            player = settings.multi_bot[0]
        except AttributeError:
            player = Player(key=settings.api_key, server=settings.game_server, user_agent=settings.user_agent)
        manager.players.append(player)
        manager.initialise_bots()

        do_nothing = lambda bot: bot

        t = threading.Thread(target=manager.run, args=(do_nothing,))
        t.daemon = True
        t.start()

        return next(iter(manager.bots), None)
    bot = test_bot()
    del test_bot
