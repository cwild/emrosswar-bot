"""
Define the interactions between a hero and his world!
"""
import logging

from emross.api import EmrossWar

logger = logging.getLogger(__name__)

class Hero(object):
    TEN = 'e'
    JACK = 'd'
    QUEEN = 'c'
    KING = 'b'
    ACE = 'a'

    RANKS = {
        TEN: '10',
        JACK: 'Jack',
        QUEEN: 'Queen',
        KING: 'King',
        ACE: 'Ace'
    }

    CLUBS = 4
    DIAMONDS = 1
    HEARTS = 2
    SPADES = 3

    FACES = {
        CLUBS: 'Clubs',
        DIAMONDS: 'Diamonds',
        HEARTS: 'Hearts',
        SPADES: 'Spades'
    }

    # Attributes
    ATTACK = 'p'
    DEFENSE = 'c1'
    COMMAND = 'c2'
    EXPERIENCE = 'ex'
    GUARDING = 'fy'
    LEVEL = 'g'
    STATE = 's'
    TARGET_EXPERIENCE = 'te'
    TOTAL_LOSSES = 'tl'
    TOTAL_WINS = 'tw'
    VIGOR = 'e'
    WINS = 'w'
    WISDOM = 'i'

    ATTRIBUTE_NAMES = {
        ATTACK: EmrossWar.LANG.get('ATTACK', 'Attack'),
        DEFENSE: EmrossWar.LANG.get('DEFENSE', 'Defense'),
        COMMAND: EmrossWar.LANG.get('MAXTROOP', 'Command'),
        LEVEL: EmrossWar.LANG.get('LEVEL', 'Level'),
        WISDOM: EmrossWar.LANG.get('WISDOM', 'Wisdom')
    }

    # States
    AVAILABLE = 0
    CAPTURED = 3
    DEAD = 2
    LOOTING = 1
    MOVING = 6
    WAR = 4
    WORKING = 5

    def __init__(self, data = {}):
        self.data = data

    def update(self, data):
        self.data = data

    @property
    def client(self):
        return EmrossWar.HERO[str(self.data.get('gid'))]

    def stat(self, attribute):
        return self.data.get(attribute, None)

    def __repr__(self):
        hero_data = self.client
        parts = [hero_data.get('name', 'Unknown')]

        parts.append('(')

        if 'rank' in hero_data:
            parts.append('%s' % self.RANKS.get(hero_data['rank']))

        if 'race' in hero_data:
            parts.append(' of %s' % self.FACES.get(hero_data['race']))

        parts.append(')')

        return ''.join(parts)
