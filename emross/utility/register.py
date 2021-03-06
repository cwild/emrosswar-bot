import argparse
import logging
import uuid

from emross.exceptions import EmrossWarApiException
from emross.api import EmrossWarApi

api = EmrossWarApi(None, None)
api.bot = None

logger = logging.getLogger(__name__)

def register(username=None, password=None, referrer=None, server=None, captcha=None):
    """
    user=creative&action=reg&referer=rm9y5w&code=875628a8-ccf7-11e0-9fbd-00216b4d955c
    """
    logger.info('Register user={0}, password={1}, referrer={2}, server={3}'.format(\
        username, password, referrer, server))

    _hash = uuid.uuid4()
    logger.info('Use hash {0}'.format(_hash))

    json = api._call('info.php',
        server=server or 'm.emrosswar.com',
        user=username,
        action='reg',
        referer=referrer,
        code=_hash,
        key=None, handle_errors=False)

    logger.info(json)
    """
    {'code': 11, 'ret': {'refercode': 'yourReferCode', 'referer': 'referedBy', 'server': 'http://sXX.emrosswar.com/'}}
    http://s37.emrosswar.com/register_api.php?jsonpcallback=jsonp1314042212580&_=1314042243901&txtUserName=test&txtPassword=Test&referer=&txtEmail=&code=c85276d5a72acf65eab074a6d10c67872bce4360&sign=51b3cebbf577f212069dc48739250d71
    """

    try:
        json = api._call('register_api.php',
            server=json['ret']['server'][7:-1],
            txtUserName=json['ret']['refercode'],
            txtPassword=password,
            referer=json['ret']['referer'],
            txtEmail='',
            picture=captcha,
            key=False, handle_errors=False)

        logger.info(json)

        if json['code'] == 20000:
            logger.error('You need to solve a captcha. Try again by passing the code with --captcha/-c')
            import webbrowser
            webbrowser.open(json['ret']['url'])
            raise EmrossWarApiException('Unable to create account {0}'.format(username))

    except TypeError as e:
        logger.exception(e)
        logger.warning('There was an error during registration.')




if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        argument_default=argparse.SUPPRESS,
        description='Register a new Emross Wars account.',
        epilog='%(prog)s -u username -p password -r refercode'
        )
    parser.add_argument('-u', '--username', help='Account username', default=None, required=True)
    parser.add_argument('-p', '--password', help='Account password', default=None, required=True)
    parser.add_argument('-r', '--referrer', help='Account refer code', default=None)
    parser.add_argument('-s', '--server', help='Game "MASTER" server', default=None)
    parser.add_argument('-c', '--captcha', help='captcha', default=None)
    parser.add_argument('-n', '--number', help='number of accounts to make', default=None, type=int)
    parser.add_argument('-o', '--offset', help='account offset', default=0, type=int)

    args = parser.parse_args()

    try:
        if args.number is None:
            register(args.username, args.password, args.referrer, args.server, args.captcha)
        else:
            for i in xrange(1 + args.offset, 1 + args.number + args.offset):
                register('{0}:{1}'.format(args.username, i),
                    args.password, args.referrer, args.server, args.captcha
                )
    except EmrossWarApiException as e:
        logger.error(e)
