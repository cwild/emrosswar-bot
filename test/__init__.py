import emross.utility.settings
emross.utility.settings.load('test.test_settings')

from dummy_bot import bot

from emross import reactor
from twisted.trial import unittest


"""
Hackish way to workaround a dirty reactor during testing!
Further details below:
https://twistedmatrix.com/trac/ticket/1964
https://tahoe-lafs.org/trac/pyutil/browser/trunk/pyutil/testutil.py?rev=249#L66
"""
#import twisted.internet.base
#twisted.internet.base.DelayedCall.debug = True

class TestCase(unittest.TestCase):
    def tearDown(self):
        for pending in emross.reactor.getDelayedCalls():
            if pending.active():
                pending.cancel()

unittest.TestCase = TestCase
del TestCase
