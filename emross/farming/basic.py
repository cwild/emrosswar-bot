import logging
import time

from emross.api import EmrossWar
from emross.exceptions import (EmrossWarApiException,
    InsufficientSoldiers,
    NoTargetsAvailable,
    NoTargetsFound)
from emross.favourites import Favourites

MINUTE = 60

logger = logging.getLogger(__name__)

import settings

def run_bot(bot):
    """
    Steps necessary for the bot to "play" the game
    """
    logger.info('Starting bot')
    logger.debug('Farming hours: {0}'.format(getattr(settings, 'farming_hours', None)))

    while bot.runnable:
        try:
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
            time.sleep(60*MINUTE)

    bot.disconnect()
