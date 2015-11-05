import collections
import hashlib
import logging
import os
import threading
import time
import urllib3

try:
    import simplejson
except ImportError:
    import json as simplejson

import emross

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
    lock = threading.Lock()
    pool = urllib3.PoolManager()
    FILE_HASHES = {}

    @classmethod
    def load(cls, filename, decoder=json_decoder, force=False, fatal=False, **kwargs):
        if cls.FILE_HASHES.get(emross.master) is None:
            cls.FILE_HASHES[emross.master] = {}
            _init_cache(emross.master)

        with cls.lock:
            filename = filename % {'lang': emross.lang}
            logger.debug('Checking "%s"' % filename)
            content = None
            localfile = os.path.join(CACHE_PATH, emross.master, filename)
            logger.debug('Local file = %s', localfile)

            target_dir = os.path.dirname(localfile)
            if not os.path.exists(target_dir):
                logger.debug('Create target directory "%s"' % target_dir)
                os.makedirs(target_dir)

            if force is False and filename == 'md5.dat':
                pass
            elif force or filename not in cls.FILE_HASHES[emross.master] or \
                cls.check_hash(localfile) != cls.FILE_HASHES[emross.master].get(filename):
                # We need to download the file
                r = cls.get_file(filename, **kwargs)
                if r.status == 200:
                    content = r.data

                    with open(localfile, 'wb') as fp:
                        fp.writelines(content)
                else:
                    logger.critical('Unable to load file %s', filename)
                    if fatal:
                        raise Exception('Unable to obtain critical data file')

            # Load the localfile from disk
            if not content:
                try:
                    logger.debug('Load "%s" from cache' % localfile)
                    fp = open(localfile, 'rb')
                    content = fp.read()
                except IOError:
                    # We should have been able to locate this file.
                    return None

            # Return our decoded content, if a decoder is available
            return decoder(content) if decoder else content

    @classmethod
    def get_file(cls, filename, **kwargs):
        logger.info('Download file "%s"' % filename)
        return cls.pool.request('GET', os.path.join(DATA_URL % emross.master, filename), headers={'User-Agent': USER_AGENT}, **kwargs)

    @classmethod
    def check_hash(cls, filename):
        try:
            with open(filename, 'rb') as fp:
                hash = hashlib.md5()
                while True:
                    piece = fp.read(1024*8)
                    if piece:
                        hash.update(piece)
                    else:
                        d = hash.hexdigest()
                        logger.debug('MD5 sum = %s' % d)
                        return d
        except IOError as e:
            logger.warning(e)
            return False


class InternalCache(object):
    lock = threading.RLock()
    DATA = collections.defaultdict(dict)
    TEMPLATES = {}


class EmrossCache(type):
    """
    Meta-class for dynamic expansion of EmrossWar class
    """
    _cache = InternalCache()

    def extend(self, key, value, model=None, **kwargs):
        cache = self.__class__._cache

        with cache.lock:
            if key not in cache.DATA[emross.master]:

                # Save for later!
                if key not in cache.TEMPLATES:
                    cache.TEMPLATES[key] = dict(value=value, model=model, **kwargs)

                filename = value
                value = EmrossContent.load(value, **kwargs)
                if model:
                    value = model(filename, value)
                cache.DATA[emross.master][key] = value

    def __getattr__(self, name):
        cache = self.__class__._cache

        with cache.lock:
            val = cache.DATA[emross.master].get(name)
            if val:
                return val
            elif name in cache.TEMPLATES:
                self.extend(name, **cache.TEMPLATES[name])
                return cache.DATA[emross.master].get(name)

        raise AttributeError(name)


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
def _init_cache(master):
    logger.info('Initialise cache using master server "%s"', master)
    try:
        force = os.path.getmtime(os.path.join(CACHE_PATH, master, 'md5.dat'))+86400 < time.time()
    except (IOError, OSError):
        force = True

    EmrossContent.FILE_HASHES[master] = dict((v, k) for k, v in [(part.split(',')) \
        for part in EmrossContent.load('md5.dat', None, force, redirect=False, fatal=True).split(';') if len(part) > 0])
