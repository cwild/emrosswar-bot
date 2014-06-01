from emross.research.tech import Tech
from emross.utility.task import CostCalculator

class Soldier(CostCalculator):
    REMAINING = '*'

    INFANTRY = 1
    SPY = 2
    PORTER = 3
    PROTECTOR = 4
    ARCHER = 5
    LANCER = 6
    HUNTER = 7
    LONUFAL = 8
    STARSLAYER = 9
    CARRIER = 10
    BERSERKER = 11
    HELFIRE = 12
    GUARDIAN = 13
    MASTER = 14
    OVERLORD = 15
    NANUH = 16
    KAHKLEH = 17
    ASSASSIN = 18

    COST_MODIFIER = 0
    COSTS = {
        INFANTRY: {
            "g": 10,
            "w": 0,
            "f": 10,
            "i": 150,
            "t": 12,
            "v": 0
        },
        SPY: {
            "g": 100,
            "w": 0,
            "f": 500,
            "i": 2000,
            "t": 30,
            "v": 0
        },
        PORTER: {
            "g": 50,
            "w": 2000,
            "f": 100,
            "i": 2000,
            "t": 48,
            "v": 0
        },
        PROTECTOR: {
            "g": 30,
            "w": 0,
            "f": 30,
            "i": 500,
            "t": 36,
            "v": 0
        },
        ARCHER:  {
            "g": 30,
            "w": 300,
            "f": 25,
            "i": 300,
            "t": 36,
            "v": 0
        },
        LANCER: {
            "g": 40,
            "w": 200,
            "f": 50,
            "i": 500,
            "t": 60,
            "v": 0
        },
        HUNTER: {
            "g": 50,
            "w": 200,
            "f": 80,
            "i": 300,
            "t": 90,
            "v": 0
        },
        LONUFAL: {
            "g": 12000,
            "w": 15000,
            "f": 15000,
            "i": 15000,
            "t": 1530,
            "v": 0
        },
        STARSLAYER: {
            "g": 220,
            "w": 1000,
            "f": 300,
            "i": 1000,
            "t": 144,
            "v": 0
        },
        CARRIER: {
            "g": 500,
            "w": 5000,
            "f": 1000,
            "i": 3000,
            "t": 120,
            "v": 0
        },
        BERSERKER: {
            "g": 700,
            "w": 2000,
            "f": 500,
            "i": 1000,
            "t": 180,
            "v": 0
        },
        HELFIRE: {
            "g": 800,
            "w": 2000,
            "f": 800,
            "i": 2000,
            "t": 240,
            "v": 0
        },
        GUARDIAN: {
            "g": 1000,
            "w": 3000,
            "f": 1000,
            "i": 3000,
            "t": 300,
            "v": 0
        },
        MASTER: {
            "g": 1300,
            "w": 4000,
            "f": 1200,
            "i": 4000,
            "t": 360,
            "v": 0
        },
        OVERLORD: {
            "g": 1500,
            "w": 4500,
            "f": 1500,
            "i": 4500,
            "t": 480,
            "v": 0
        },
        NANUH: {
            "g": 3000,
            "w": 6000,
            "f": 3000,
            "i": 6000,
            "t": 1530,
            "v": 0
        },
        KAHKLEH: {
            "g": 4500,
            "w": 7000,
            "f": 5000,
            "i": 7000,
            "t": 1530,
            "v": 0
        },
        ASSASSIN: {
            "g": 9000,
            "w": 9500,
            "f": 9000,
            "i": 9000,
            "t": 120,
            "v": 0
        }
    }

    @classmethod
    def cost(cls, troop, quantity, *args, **kwargs):
        return super(Soldier, cls).cost(troop, modifier=quantity-1)


class SoldierStat:
    ATTACK = 'a'
    CRITICAL = 'e'
    DEFENSE = 'd'
    HEALTH = 'h'
    SPEED = 's'
    UPKEEP = 'f'


DEFAULT_SOLDIER_STAT_MODIFIERS = {
    SoldierStat.ATTACK: lambda total, tech_level: total * (0.005 + \
            ((tech_level(Tech.ADVANCED_WEAPON) * 0.025) + \
            tech_level(Tech.ATTACK_FORMATION) * 0.025) / 100),

    SoldierStat.DEFENSE: lambda total, tech_level: total * (0.005 + \
            ((tech_level(Tech.ADVANCED_ARMOUR) * 0.025) + \
            tech_level(Tech.DEFENSE_FORMATION) * 0.025) / 100)
}

SOLDIER_STAT_MODIFIERS = {
    # Use DEFAULT formulae for this
    Soldier.KAHKLEH: DEFAULT_SOLDIER_STAT_MODIFIERS
}

SOLDIER_STAT_MODIFIERS[Soldier.BERSERKER] = SOLDIER_STAT_MODIFIERS[Soldier.KAHKLEH]
SOLDIER_STAT_MODIFIERS[Soldier.MASTER] = SOLDIER_STAT_MODIFIERS[Soldier.KAHKLEH]
SOLDIER_STAT_MODIFIERS[Soldier.OVERLORD] = SOLDIER_STAT_MODIFIERS[Soldier.KAHKLEH]


if __name__ == "__main__":
    print Soldier.COSTS[Soldier.OVERLORD]
    print Soldier.cost(Soldier.OVERLORD, quantity=1)
    print Soldier.cost(Soldier.OVERLORD, quantity=10)
