#!/usr/bin/python

import time
from helper import *
from emross import *

SECOND = 1
MINUTE = 60 * SECOND
HOUR   = 60 * MINUTE


bot = EmrossWarBot()

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

                for city in bot.cities:
                    print 'Updating city %s' % city.name
                    city.update()

                    city.recruit_hero()

                    print 'Replenishing food'
                    city.replenish_food()

                    try:
                        """
                        How many (decent) soldiers are in this city?
                        """
                        print 'Getting soldiers'
                        city.get_soldiers()

                        print 'Getting available heroes'
                        city.get_available_heroes()

                        """
                        How many armies can we form from the above number of soldiers?
                        """
                        armies = city.get_army_count()
                        print '%d armies in this city (%s)' % (armies, city.name)

                        for i in range(armies):
                            target = bot.find_target(EmrossWar.DEVIL_ARMY)

                            # create an army
                            army = city.create_army()

                            # choose hero which can lead this army
                            hero = city.choose_hero(sum(army.values()))

                            # send troops to attack
                            params = {
                                'action': 'do_war',
                                'attack_type': 7,
                                'gen': hero.data['gid'],
                                'area': target.y,
                                'area_x': target.x
                            }

                            params.update(army)

                            cost = city.action_confirm(params)
                            params.update(cost)

                            print 'Sending attack %d/%d' % (target.y, target.x)
                            city.action_do(params)

                            """
                            Update cache as targets are only updated once per city rather than per hero
                            """
                            target.attack += 1

                    except AttributeError, e:
                        continue

                    except InsufficientSoldiers, e:
                        print '%s has insufficient troops to launch an attack.' % city.name
                        continue

            except NoTargetsFound:
                for city in bot.cities:
                    city.recruit_hero()

                print 'No targets found'

                print 'Processing scout reports'
                bot.scout_map()

                print 'Checking for new fav Devil Armies'
                bot.get_fav(EmrossWar.DEVIL_ARMY)

                if len([f for f in bot.fav[EmrossWar.DEVIL_ARMY] if f.attack < settings.npc_attack_limit]):
                    tl = ([f for f in bot.fav[EmrossWar.DEVIL_ARMY] if f.attack < settings.npc_attack_limit])
                    for t in tl:
                        print 'Coord %d,%d, Attack %d' % (t.x, t.y, t.attack)
                    print 'We have some more Devil Armies to attack!'
                else:
                    print 'None found, sleep for 30 minutes'
                    time.sleep(30*MINUTE)

                continue


            """
            Now wait a while for things to return to their respective city
            """
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