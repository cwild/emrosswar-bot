"""
This is a placeholder. We should install settings here such as:

import emross.utility.settings
settings = emross.utility.settings.load('my_settings_file')
"""
import importlib
import logging
import sys

logger = logging.getLogger(__name__)

class Settings(object):
    """
    This module is represented by this class
    """

    def __init__(self, wrapped):
        self.wrapped = wrapped

    def __repr__(self):
        # Mask the fact we are an instance of this class!
        return str(self.wrapped)

    def load(self, *args, **kwargs):
        logger.debug('Loading settings file: {0}, {1}'.format(args, kwargs))
        data = importlib.import_module(*args, **kwargs)
        self.__dict__.update(data.__dict__)
        return self

    def __getattr__(self, name):
        return getattr(self.__dict__, name)

    def __setattr__(self, name, val):
        self.__dict__[name] = val


sys.modules[__name__] = Settings(sys.modules[__name__])
