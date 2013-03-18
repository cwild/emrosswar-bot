"""
Attributes of Emross heroes
"""

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

    ATTACK = "p"
    DEFENSE = "c1"
    COMMAND = "c2"
    EXPERIENCE = "ex"
    LEVEL = "g"
    VIGOR = "e"
    WISDOM = "i"

    def __init__(self, data = {}):
        self.data = data

    def update(self, data):
        self.data = data

    def __repr__(self):
        parts = [self.data.get('name', 'Unknown')]

        parts.append('(')

        if 'rank' in self.data:
            parts.append('%s' % self.RANKS.get(self.data['rank']))

        if 'race' in self.data:
            parts.append(' of %s' % self.FACES.get(self.data['race']))

        parts.append(')')

        return ''.join(parts)
