from twisted.internet import defer, reactor
from twisted.python import log
observer = log.PythonLoggingObserver()
observer.start()

def deferred_sleep(delay):
    d = defer.Deferred()
    delay = reactor.callLater(delay, d.callback, True)
    d.delay = delay
    return d

import gettext
gettext.install(
    'emrosswar-bot',
    'resources/locale',
    unicode=True,
    names=('gettext', 'ngettext')
)

device = 'EW-IPAD'
lang = 'en'
master = 'm.emrosswar.com'

"""
Players whom can control the bot! (applies to all bots)
"""
OPERATORS = []
