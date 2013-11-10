from emross.mobs.ally import alliance

commanders = []
units = []

class DevilArmy:
    ONE_STAR = 6
    TWO_STAR = 5
    THREE_STAR = 4
    FOUR_STAR = 3
    FIVE_STAR = 2
    SIX_STAR = 1
    SEVEN_STAR = 7
    EIGHT_STAR = 8


class Hero(object):
    BASE_ATTACK = 50
    BASE_DEFENSE = 30

    def __init__(self, name, **kwargs):
        self.name = name
        self.attack = kwargs.get('attack', self.BASE_ATTACK)
        self.defense = kwargs.get('defense', self.BASE_DEFENSE)

class Unit(object):
    BASE_ATTACK = 200
    BASE_DEFENSE = 100
    BASE_CRITICAL = 250

    def __init__(self, name, **kwargs):
        self.name = name
        self.attack = kwargs.get('attack', self.BASE_ATTACK)
        self.defense = kwargs.get('defense', self.BASE_DEFENSE)
        self.critical = kwargs.get('critical', self.BASE_CRITICAL)
