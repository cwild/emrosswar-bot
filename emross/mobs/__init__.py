from __future__ import division

from emross.api import EmrossWar
from emross.arena.hero import Hero as BaseHero
from emross.military.camp import SoldierStat
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
    NINE_STAR = 9
    TEN_STAR = 10

class Colony:
    SMALL_FARM = 101
    MEDIUM_FARM = 102
    LARGE_FARM = 103
    HUGE_FARM = 104
    SMALL_FOREST = 111
    MEDIUM_FOREST = 112
    LARGE_FOREST = 113
    HUGE_FOREST = 114
    SMALL_IRON = 121
    MEDIUM_IRON = 122
    LARGE_IRON = 123
    HUGE_IRON = 124

class Hero(BaseHero):
    BASE_ATTACK = 50
    BASE_DEFENSE = 30

    def __init__(self, name, **kwargs):
        super(Hero, self).__init__(**kwargs)
        self.name = name
        self.attack = self.data[BaseHero.ATTACK] = kwargs.get('attack', self.BASE_ATTACK)
        self.defense = self.data[BaseHero.DEFENSE] = kwargs.get('defense', self.BASE_DEFENSE)


class Unit(object):
    BASE_ATTACK = 200
    BASE_DEFENSE = 100
    BASE_CRITICAL = 100

    UNITS = []

    def __init__(self, name, rating, alias='*Unknown Unit*', **kwargs):
        self._name = name
        self.alias = alias
        self.rating = rating
        self.data = {}
        self.attack = self.data[SoldierStat.ATTACK] = kwargs.get('attack', self.BASE_ATTACK)
        self.defense = self.data[SoldierStat.DEFENSE] = kwargs.get('defense', self.BASE_DEFENSE)
        self.critical = self.data[SoldierStat.CRITICAL] = kwargs.get('critical', self.BASE_CRITICAL)

        self.__class__.UNITS.append(self)

    @property
    def name(self):
        return self._name or self.alias

    @classmethod
    def soldier_data(cls, troop):
        return troop.data

    @classmethod
    def find(cls, name, rating):
        for unit in cls.UNITS:
            if name == unit._name and rating == unit.rating:
                return unit

        try:
            ratings = range(6, 0, -1) + range(7, 9)
            raise ValueError('No NPC Unit named "{0}" ({1}* {2}) found.'.format(name,
                ratings[rating-1], EmrossWar.LANG.get('MONSTER', 'DevilArmy')))
        except IndexError:
            raise ValueError('No NPC Unit named "{0}" found.'.format(name))


    def __repr__(self):
        return '{0}(name={1}, rating={2})'.format(self.__class__.__name__,
            self._name or '"{0}"*'.format(self.alias),
            self.rating
        )
