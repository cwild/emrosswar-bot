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
        pickle.dump(self, open(self.PATH % self.key, 'wb'))

    @classmethod
    def load(cls, key):
        try:
            session = pickle.load(open(cls.PATH % key, 'rb'))
            session.key = key
            return session
        except IOError:
            return Session(key)
