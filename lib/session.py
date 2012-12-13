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
        with open(self.PATH % self.key, 'wb') as fp:
            pickle.dump(self, fp)

    @classmethod
    def load(cls, key):
        try:
            with open(cls.PATH % key, 'rb') as fp:
                session = pickle.load(fp)
            session.key = key
            return session
        except IOError:
            return Session(key)
