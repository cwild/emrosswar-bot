import argparse
import logging
import uuid

from emross.exceptions import EmrossWarApiException
from emross.api import EmrossWarApi

api = EmrossWarApi(None, None)
api.bot = None

logger = logging.getLogger(__name__)

def register(username=None, password=None, referrer=None, server=None):
    """
    user=creative&action=reg&referer=rm9y5w&code=875628a8-ccf7-11e0-9fbd-00216b4d955c
    """
    json = api._call('info.php',
        server=server or 'm.emrosswar.com',
        user=username,
        action='reg',
        referer=referrer,
        code=uuid.uuid4(),
        key=None, handle_errors=False)

    logger.info(json)
    """
    {'code': 11, 'ret': {'refercode': 'yourReferCode', 'referer': 'referedBy', 'server': 'http://sXX.emrosswar.com/'}}
    http://s37.emrosswar.com/register_api.php?jsonpcallback=jsonp1314042212580&_=1314042243901&txtUserName=test&txtPassword=Test&referer=&txtEmail=&code=c85276d5a72acf65eab074a6d10c67872bce4360&sign=51b3cebbf577f212069dc48739250d71
    """

    try:
        api._call('register_api.php',
            server=json['ret']['server'][7:-1],
            txtUserName=json['ret']['refercode'],
            txtPassword=password,
            referer=json['ret']['referer'],
            txtEmail='',
            key=False, handle_errors=False)
    except TypeError as e:
        logging.exception(e)
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

    args = parser.parse_args()

    try:
        register(args.username, args.password, args.referrer, args.server)
    except EmrossWarApiException, e:
        logging.exception(e)
