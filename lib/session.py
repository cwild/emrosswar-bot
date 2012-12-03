try:
    import cPickle as pickle
except ImportError, e:
    import pickle

class Session:
    #__module__ = os.path.splitext(os.path.basename(__file__))[0]
    PATH = 'build/session.%s.pickle'

    def __init__(self, key):
        self.key = key

    def save(self):
        pickle.dump(self, file(self.PATH % self.key, 'wb'))

    @classmethod
    def load(cls, key):
        try:
            return pickle.load(file(cls.PATH % key))
        except IOError:
            return Session(key)
