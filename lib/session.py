#import os
import pickle

class Session:
    #__module__ = os.path.splitext(os.path.basename(__file__))[0]
    PATH = 'build/session.pickle'

    def save(self):
        pickle.dump(self, file(self.PATH, 'w'))

    @classmethod
    def load(cls):
        try:
            return pickle.load(file(cls.PATH))
        except IOError:
            return Session()
