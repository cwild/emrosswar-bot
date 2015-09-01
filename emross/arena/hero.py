"""
Define the interactions between a hero and his world!
"""
import re

from emross.api import EmrossWar
from emross.utility.base import EmrossBaseObject

from lib import six

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

    FACE_SYMBOLS = {
        CLUBS: six.u('\u2660'),
        DIAMONDS: six.u('\u2666'),
        HEARTS: six.u('\u2665'),
        SPADES: six.u('\u2663')
    }

    # Attributes
    ATTACK = 'p'
    DEFENSE = 'c1'
    COMMAND = 'c2'
    EXPERIENCE = 'ex'
    GUARDING = 'fy'
    HERO_ID = 'gid'
    LEVEL = 'g'
    LOYALTY = 'f'
    REBORN = 'reborn'
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

    MIN_LEVEL = 1
    MAX_LEVEL = 38

    def __init__(self, data={}, gear={}, **kwargs):
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

    def can_reborn(self):
        return bool(self.data.get('showReborn', False))

    def stat(self, attribute, default=None):
        return self.data.get(attribute, default)

    def __repr__(self):
        hero_data = self.client
        parts = [hero_data.get('name', 'Unknown')]

        if 'rank' in hero_data:
            parts.append('%s' % self.RANKS.get(hero_data['rank']))

        if 'race' in hero_data:
            parts.append(' of %s' % self.FACES.get(hero_data['race']))

        if len(parts) > 1:
            parts.insert(1, '(')
            parts.append(')')

        return ''.join(parts)

    @classmethod
    def find(cls, search=None, *args, **kwargs):
        result = {}
        try:
            hero_id = int(search)
            data = EmrossWar.HERO.get(str(hero_id))
            if data:
                result['hero_id'] = hero_id
                result.update(data)
        except ValueError:
            for hero_id, data in EmrossWar.HERO.iteritems():
                if re.search(search, data.get('name'), re.IGNORECASE):
                    result['hero_id'] = int(hero_id)
                    result.update(data)
                    break

        return result