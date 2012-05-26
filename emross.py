

class EmrossWar:
    SUCCESS = 0
    ERROR_UNKNOWN = -1
    ERROR_INVALID_KEY = 2
    #ERROR_AUTHFAIL = {12:1, 14:1, 301:1, 302:1}


    """
    3: "Scout",
    0: "Loot",
    7: "Attack",
    8: "Occupy",
    9: "Conquer",
    5: "Build",
    2: "Transport"
    """
    ATTACK_TYPE_SCOUT = 3
    ACTION_ATTACK = 7


    LORD = 1
    DEVIL_ARMY = 2
    COLONY = 3



    REACHED_HERO_LIMIT = 1304
    RECRUITING_CLOSED  = 1305
    INSUFFICIENT_GOLD  = 1306


    PVP_ELIMINATED = 7415

class Soldier:
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


class DevilArmy:
    ONE_STAR = 6
    TWO_STAR = 5
    THREE_STAR = 4
    FOUR_STAR = 3
    FIVE_STAR = 2
    SIX_STAR = 1
