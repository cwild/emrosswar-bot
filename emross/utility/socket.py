import atexit
import logging
import sys
sys.path.extend(['lib/'])

from emross.utility.remote_api import RemoteApi

import settings

logger = logging.getLogger(__name__)


def close_connection(conn):
    logger.debug('Try to close the established connection')
    conn.queue_out.put(None) # poison pill!
    conn.process.terminate()

def establish_connection():
    """
    Connect to our standard API and find a socket server to use
    """
    remote_api = RemoteApi(**settings.plugin_api)

    json = remote_api.call('socket/discover')

    import emross_socket_client
    sock = emross_socket_client.connect(**json)

    # Try to clean-up when the program is exiting
    atexit.register(close_connection, sock)

    return sock
