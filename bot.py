import logging
import re

"""
If logging hasn't already been configured, setup our own from logging.conf files
"""
if len(logging.root.handlers) == 0:
    from lib import six
    import logging.config

    try:
        logging.config.fileConfig('build/logging.conf')
    except six.moves.configparser.NoSectionError:
        logging.config.fileConfig('logging.conf')



import emross.utility.settings
from emross.utility.manager import BotManager
from emross.utility.player import Player


logger = logging.getLogger(__name__)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        argument_default=argparse.SUPPRESS,
        description=gettext('The EmrossWar Bot'),
        epilog='%(prog)s --multi'
        )
    parser.add_argument('-m', '--multi', help='Multiple players at once!', action='store_true', default=False)
    parser.add_argument('-c', '--console', help='Interactive console', action='store_true', default=False)
    parser.add_argument('-p', '--poolsize', help='Number of threads to use in the pool', type=int, default=None)
    parser.add_argument('-s', '--socket', help='Establish a bi-directional server socket', action='store_true', default=False)
    parser.add_argument('--settings', help='Which settings file should we use?', type=str, default='settings')
    args = parser.parse_args()

    # Application settings, configurable
    settings = emross.utility.settings.load(re.sub('\.py$', '', args.settings))

    try:
        import emross.handlers
        emross.handlers.handlers[settings.TOO_OFTEN_WARNING] = emross.handlers.VisitTooOftenHandler
    except AttributeError:
        raise AttributeError('You need to set the API TOO_OFTEN_WARNING code in your settings file')

    manager = BotManager(console=args.console, processes=args.poolsize, \
                        socket=args.socket, settings=settings)

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

        manager.run()

    except KeyboardInterrupt:
        logger.critical('Caught KeyboardInterrupt, begin shutdown')

        for bot in manager.bots:
            bot.shutdown()

    logger.info('Exiting')

else:
    def test_bot():
        settings = emross.utility.settings.load('settings')
        try:
            player = settings.multi_bot[0]
        except AttributeError:
            player = Player(key=settings.api_key, server=settings.game_server, user_agent=settings.user_agent)

        manager = BotManager()
        manager.players.append(player)
        manager.run(workhorse=False)

        return next(iter(manager.bots), None)
    bot = test_bot()
    del test_bot
