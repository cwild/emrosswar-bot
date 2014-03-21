import logging
import threading

from emross.utility.remote_api import RemoteApi

BASE_URL = 'https://api.pushover.net/1/'
MESSAGE_URL = BASE_URL + 'messages.json'
USER_URL = BASE_URL + 'users/validate.json'
SOUND_URL = BASE_URL + 'sounds.json'
RECEIPT_URL = BASE_URL + 'receipts/'

LOCK = threading.Lock()
logger = logging.getLogger(__name__)


class _Pushover(RemoteApi):
    SOUNDS = {}

    def __init__(self, **kwargs):
        super(_Pushover, self).__init__(url=BASE_URL, auth=None)
        self.kwargs = kwargs
        self.initialised = 'token' in kwargs and 'user' in kwargs

    def call(self, *args, **kwargs):
        logger.debug('Pushover call: args={0}, kwargs={1}'.format(args, kwargs))

        if not self.initialised:
            return

        """
        header: X-Limit-App-Limit: 7500
        header: X-Limit-App-Remaining: 7496
        header: X-Limit-App-Reset: 1396328400
        """

        with LOCK:
            payload = {}
            payload.update(self.kwargs)
            payload.update(kwargs)
            return super(_Pushover, self).call(*args, **payload)

    def send_message(self, message, title=None, **kwargs):
        return self.call(MESSAGE_URL, message=message, title=title, **kwargs)

    def sounds(self):
        if not self.SOUNDS:
            try:
                self.SOUNDS =  self.call(SOUND_URL, method='GET', user=None)['sounds']
            except KeyError as e:
                logger.exception(e)

        return self.SOUNDS



import settings
params = getattr(settings, 'plugin_api', {}).get('pushover', {})
Pushover = _Pushover(**params)

__all__ = ['Pushover']


if __name__ == "__main__":
    import random
    sounds = Pushover.sounds()
    sound = random.choice(list(sounds.keys()))

    r = Pushover.send_message(
        message='This is a test message! http://emross.cryformercy.com "{0}"!'.format(sounds.get(sound)),
        title='Pushover Test',
        sound=sound
    )

    print r
