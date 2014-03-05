import logging
import time

logger = logging.getLogger(__name__)

class _DummyWith(object):
    def __enter__(self): pass
    def __exit__(self, type, value, traceback): return True
_with = _DummyWith()

class CacheableData(object):
    LOCKED = False

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

    def __len__(self):
        return len(self.data)

    @property
    def _lock(self):
        """
        Locking should be provided by subclass
        """
        try:
            return self.lock
        except AttributeError:
            return _with

    @property
    def data(self):
        with self._lock:
            try:
                should_update = self.should_update()
            except Exception:
                should_update = False

            if self.LOCKED:
                self.log.debug('Data is locked from auto-updating')
            elif time.time() > self._expires or should_update:
                self.data = self.update(*self.args, **self.kwargs)

        return self._data

    @data.setter
    def data(self, value):
        with self._lock:
            if isinstance(value, dict):
                # Default to 0 so we can pass our own dict straight through
                if value.get('code', 0) != 0:
                    return
                value = value.get('ret', value)

            if value is not None:
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
    logger.info('len={0}'.format(len(d)))
    logger.info(d.data)
    logger.info('len={0}'.format(len(d)))
    d.data = {'code':0, 'ret': {'b':1}}
    logger.info(d.data)
    logger.info(d['b'])

    d.data = {'code':1, 'ret': {'b':2}}
    logger.info(d['b'])
    logger.info('len={0}'.format(len(d)))
