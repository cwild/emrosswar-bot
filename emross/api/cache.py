import collections
import hashlib
import logging
import os
import time

try:
    import simplejson
except ImportError:
    import json as simplejson

import emross
from emross.api import agent, Headers, read_body

logger = logging.getLogger(__name__)

CACHE_PATH = 'build/cache/'
DATA_URL =  'http://%s/ver_ipad/build/'
USER_AGENT = 'EmrossWar/1.42 CFNetwork/548.1.4 Darwin/11.0.0'

def json_decoder(data):
    s = data[ data.find('{') : data.rfind('}')+1 ]
    try:
        return simplejson.loads(s)
    except ValueError as e:
        logger.debug(e)
        return {}

class EmrossContent(object):
    lock = emross.defer.DeferredLock()
    FILE_HASHES = {}

    @classmethod
    @emross.defer.inlineCallbacks
    def load(cls, filename, decoder=json_decoder, force=False, fatal=False, **kwargs):
        if cls.FILE_HASHES.get(emross.master) is None:
            logger.debug('Check validity of master server: %s', emross.master)
            domain_check = emross.reactor.resolve(emross.master, timeout=(5,))
            domain_check.addCallback(lambda ip: logger.debug((emross.master, ip)))

            def error_handler(error):
                logger.error(error)
                emross.reactor.stop()
            domain_check.addErrback(error_handler)

            yield domain_check

            cls.FILE_HASHES[emross.master] = {}
            yield _init_cache(emross.master)

        filename = filename % {'lang': emross.lang}
        logger.debug('Checking "%s"', filename)
        content = None
        localfile = os.path.join(CACHE_PATH, emross.master, filename)
        logger.debug('Local file = %s', localfile)

        target_dir = os.path.dirname(localfile)
        if not os.path.exists(target_dir):
            logger.debug('Create target directory "%s"', target_dir)
            os.makedirs(target_dir)

        if force is False and filename == 'md5.dat':
            hash = None
        else:
            hash = yield cls.check_hash(localfile)

        if force or cls.FILE_HASHES[emross.master].get(filename) != hash:
            if hash:
                logger.debug('"%s" has failed hash, expected "%s"', filename,
                    cls.FILE_HASHES[emross.master].get(filename))

            # We need to download the file
            try:
                content = yield cls.get_file(filename, **kwargs)

                with open(localfile, 'wb') as fp:
                    fp.writelines(content)

            except Exception:
                logger.critical('Unable to load file %s', filename)
                if fatal:
                    logger.critical('Unable to obtain critical data file')
                    emross.reactor.stop()

        # Load the localfile from disk
        if not content:
            try:
                logger.debug('Load "%s" from cache', localfile)
                with open(localfile, 'rb') as fp:
                    content = fp.read()
            except IOError:
                # We should have been able to locate this file.
                emross.defer.returnValue(None)

        # Return our decoded content, if a decoder is available
        emross.defer.returnValue(decoder(content) if decoder else content)

    @classmethod
    @emross.defer.inlineCallbacks
    def get_file(cls, filename, **kwargs):
        logger.info('Download file "%s"', filename)

        response = yield agent.request('GET',
            os.path.join(DATA_URL % emross.master, filename),
            Headers({'User-Agent': [USER_AGENT]}), **kwargs
        )

        body = yield read_body(response)
        emross.defer.returnValue(body)

    @classmethod
    @emross.defer.inlineCallbacks
    def check_hash(cls, filename):
        try:
            with open(filename, 'rb') as fp:
                hash = hashlib.md5()

                while True:
                    # 1024 * 8 => 8kB
                    piece = fp.read(8192)
                    if piece:
                        yield hash.update(piece)
                    else:
                        d = yield hash.hexdigest()
                        logger.debug('MD5 sum = %s', d)
                        emross.defer.returnValue(d)
        except IOError as e:
            logger.warning(e)
            emross.defer.returnValue(False)


class InternalCache(object):
    lock = emross.defer.DeferredLock()
    DATA = collections.defaultdict(dict)
    TEMPLATES = {}


class EmrossCache(type):
    """
    Meta-class for dynamic expansion of EmrossWar class
    """
    _cache = InternalCache()

    @emross.defer.inlineCallbacks
    def extend(self, key, value, model=None, **kwargs):
        cache = self._cache

        yield cache.lock.acquire()

        try:
            if key not in cache.DATA[emross.master]:
                # Save for later!
                if key not in cache.TEMPLATES:
                    cache.TEMPLATES[key] = dict(value=value, model=model, **kwargs)

                filename = value
                value = yield EmrossContent.load(value, **kwargs)
                if model:
                    value = model(filename, value)
                cache.DATA[emross.master][key] = value
        finally:
            cache.lock.release()


    def __getattr__(self, name):
        cache = self._cache

        try:
            return cache.DATA[emross.master][name]
        except KeyError:
            pass

        @emross.defer.inlineCallbacks
        def inner():
            val = cache.DATA[emross.master].get(name)

            if val:
                emross.defer.returnValue(val)
            elif name in cache.TEMPLATES:
                yield self.extend(name, **cache.TEMPLATES[name])
                emross.defer.returnValue(cache.DATA[emross.master].get(name))

            raise AttributeError(name)

        return cache.lock.run(inner)


class EmrossDataHandler(object):
    def __init__(self, filename, data):
        self.filename = filename
        self.data = data

    def reload(self):
        self.data = EmrossContent.load(filename, force=True)

    def __getitem__(self, name):
        if name in self.data:
            return self.data[name]
        raise AttributeError(name)



# Initialise our cache
@emross.defer.inlineCallbacks
def _init_cache(master):
    logger.info('Initialise cache using master server "%s"', master)
    try:
        force = yield os.path.getmtime(os.path.join(CACHE_PATH, master, 'md5.dat'))+86400 < time.time()
    except (IOError, OSError) as e:
        force = True

    file_list = yield EmrossContent.load('md5.dat', None, force, fatal=True)

    EmrossContent.FILE_HASHES[master] = dict((v, k) for k, v in [(part.split(',')) \
        for part in file_list.split(';') if len(part) > 0])
