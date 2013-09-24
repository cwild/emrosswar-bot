"""
Define the interactions between a hero and his world!
"""

from emross.api import EmrossWar
from emross.utility.base import EmrossBaseObject


class Gear:
    WEAPON = 1
    ARMOR = 2
    MOUNT = 3
    WISDOM_BOOK = 4
    DEFENSE_BOOK = 5
    RING = 6

    WEAPON_SLOT = 1
    ARMOR_SLOT = 2
    MOUNT_SLOT = 3
    BOOK_SLOT = 4
    RING_SLOT = 5

    TYPE_SLOTS = {
        ARMOR: ARMOR_SLOT,
        DEFENSE_BOOK: BOOK_SLOT,
        MOUNT: MOUNT_SLOT,
        RING: RING_SLOT,
        WEAPON: WEAPON_SLOT,
        WISDOM_BOOK: BOOK_SLOT,
    }

    """
    [23, 0, 0, 41, 0, 0]
    [SPEED, TROOP_DEFENSE, TROOP_CARRY, ATTACK, WISDOM, DEFENSE]
    """
    SPEED = 0
    TROOP_DEFENSE = 1
    TROOP_CARRY = 2
    ATTACK = 3
    WISDOM = 4
    DEFENSE = 5


class Hero(EmrossBaseObject):
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
    LOYALTY = 'f'
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

    def __init__(self, data={}, gear={}):
        self.data = data
        self._gear = gear

    def update(self, data):
        self.data.update(data)

    @property
    def client(self):
        return EmrossWar.HERO[str(self.data.get('gid'))]

    @property
    def gear(self):
        try:
            return self._gear.data
        except AttributeError:
            return self._gear

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
