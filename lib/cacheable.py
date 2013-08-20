import logging
import time

logger = logging.getLogger(__name__)

class CacheableData(object):
    def __init__(self, time_to_live=120, update=None, *args, **kwargs):
        super(CacheableData, self).__init__()
        self._expires = 0
        self._data = {}
        self.time_to_live = time_to_live

        if update:
            self.update = update

        self.args = args
        self.kwargs = kwargs

    def __getitem__(self, val):
        return self.data.__getitem__(val)

    @property
    def data(self):
        try:
            should_update = self.should_update()
        except Exception:
            should_update = False

        if time.time() > self._expires or should_update:
            self.data = self.update(*self.args, **self.kwargs)
        return self._data

    @data.setter
    def data(self, value):
        if isinstance(value, dict):
            if value.get('code') != 0:
                return
            value = value.get('ret', value)

        self._data = value
        self._expires = time.time() + self.time_to_live

    def should_update(self):
        return False

    def update(self, *args, **kwargs):
        logger.warning('No update method provided for this data handler')
        return {}

    def expire(self, clear=False):
        """
        Forces the data to be refreshed the next time it is accessed.
        Optionally, clear the existing data as well (defaults to False).
        """
        logger.debug('Reset the cached data expiry time')
        if clear:
            self._data = {}
        self._expires = 0

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    def fn(*args, **kwargs):
        logger.info(args)
        logger.info(kwargs)
        return kwargs

    d = CacheableData(5, fn, 111, method='noop', test=456)
    logger.info(d.data)
    d.data = {'code':0, 'ret': {'b':1}}
    logger.info(d.data)
    logger.info(d['b'])

    d.data = {'code':1, 'ret': {'b':2}}
    logger.info(d['b'])
