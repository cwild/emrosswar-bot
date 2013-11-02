import logging

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

from emross.utility.manager import BotManager
from emross.utility.player import Player

try:
    import emross.handlers
    emross.handlers.handlers[settings.TOO_OFTEN_WARNING] = emross.handlers.VisitTooOftenHandler
except AttributeError:
    raise AttributeError('You need to set the API TOO_OFTEN_WARNING code in your settings file')


logger = logging.getLogger(__name__)

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

        from emross.farming.basic import run_bot
        manager.run(run_bot)

    except KeyboardInterrupt:
        for bot in manager.bots:
            bot.shutdown()

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

        t = threading.Thread(target=manager.run, args=(do_nothing,False))
        t.daemon = True
        t.start()

        return next(iter(manager.bots), None)
    bot = test_bot()
    del test_bot
