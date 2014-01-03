from emross.utility.task import CostCalculator

class Tech(CostCalculator):
    FORGING = 1
    MARCHING = 2
    SCOUTING = 3
    LOGISTICS = 4
    EFFICIENT_TRAINING = 5
    ADVANCED_WEAPON = 6
    ADVANCED_ARMOUR = 7
    TAMING = 8
    DEFENSE_FACILITY = 9
    HEAVY_EQUIPMENT = 10
    TARGETING = 11
    MINING = 12
    LOGGING = 13
    ALCHEMY = 14
    AGRICULTURE = 15
    MAGIC_FORGE = 16
    ARTIFACT = 17
    ATTACK_FORMATION = 18
    DEFENSE_FORMATION = 19
    COLLECTION = 20
    ENHANCEMENT = 21
    RESCUE = 22
    RESURRECTION = 23


    COST_MODIFIER = 0.5
    COSTS = {
        FORGING: {
                "g": 100,
                "w": 500,
                "f": 100,
                "i": 750,
                "t": 720,
                "v": 0
            },
        MARCHING: {
                "g": 250,
                "w": 0,
                "f": 375,
                "i": 500,
                "t": 1140,
                "v": 0
            },
        SCOUTING: {
                "g": 250,
                "w": 0,
                "f": 250,
                "i": 500,
                "t": 960,
                "v": 0
            },
        LOGISTICS: {
                "g": 500,
                "w": 0,
                "f": 500,
                "i": 1000,
                "t": 1920,
                "v": 0
            },
        EFFICIENT_TRAINING: {
                "g": 250,
                "w": 500,
                "f": 1000,
                "i": 500,
                "t": 2340,
                "v": 0
            },
        ADVANCED_WEAPON: {
                "g": 250,
                "w": 1250,
                "f": 250,
                "i": 1250,
                "t": 3420,
                "v": 0
            },
        ADVANCED_ARMOUR: {
                "g": 500,
                "w": 2500,
                "f": 500,
                "i": 2500,
                "t": 3780,
                "v": 0
            },
        TAMING: {
                "g": 1000,
                "w": 500,
                "f": 2500,
                "i": 500,
                "t": 4800,
                "v": 0
            },
        DEFENSE_FACILITY: {
                "g": 750,
                "w": 2500,
                "f": 250,
                "i": 3750,
                "t": 5460,
                "v": 0
            },
        HEAVY_EQUIPMENT: {
                "g": 1000,
                "w": 3750,
                "f": 1000,
                "i": 2500,
                "t": 6660,
                "v": 0
            },
        TARGETING: {
                "g": 1250,
                "w": 2500,
                "f": 1500,
                "i": 3750,
                "t": 7260,
                "v": 0
            },
        MINING: {
                "g": 1250,
                "w": 0,
                "f": 2500,
                "i": 3750,
                "t": 7920,
                "v": 0
            },
        LOGGING: {
                "g": 1250,
                "w": 3750,
                "f": 2500,
                "i": 0,
                "t": 7920,
                "v": 0
            },
        ALCHEMY: {
                "g": 2500,
                "w": 2500,
                "f": 2500,
                "i": 2500,
                "t": 10080,
                "v": 0
            },
        AGRICULTURE: {
                "g": 2000,
                "w": 2500,
                "f": 3750,
                "i": 2500,
                "t": 9360,
                "v": 0
            },
        MAGIC_FORGE: {
                "g": 5000,
                "w": 10000,
                "f": 3000,
                "i": 10000,
                "t": 14580,
                "v": 0
            },
        ARTIFACT: {
                "g": 10000,
                "w": 5000,
                "f": 4000,
                "i": 5000,
                "t": 16680,
                "v": 0
            },
        ATTACK_FORMATION: {
                "g": 20000,
                "w": 20000,
                "f": 20000,
                "i": 20000,
                "t": 19860,
                "v": 0
            },
        DEFENSE_FORMATION: {
                "g": 25000,
                "w": 25000,
                "f": 25000,
                "i": 25000,
                "t": 21600,
                "v": 0
            },
        COLLECTION: {
                "g": 25000,
                "w": 25000,
                "f": 25000,
                "i": 25000,
                "t": 21600,
                "v": 0
            },
        ENHANCEMENT: {
                "g": 25000,
                "w": 25000,
                "f": 25000,
                "i": 25000,
                "t": 21600,
                "v": 0
            },
        RESCUE: {
                "g": 15000,
                "w": 15000,
                "f": 15000,
                "i": 15000,
                "t": 21600,
                "v": 0
            },
        RESURRECTION: {
                "g": 50000,
                "w": 50000,
                "f": 50000,
                "i": 50000,
                "t": 21600,
                "v": 0
            }
    }


"""
game/study_api.php city=92832
jQuery172017185111993647606_1345909039193({"code":0,"ret":
[[1,11,1],[2,10,1],[3,1,1],[4,1,1],[5,1,1],[6,15,1],[7,17,1],[8,10,1],[9,8,1],[10,10,1],[11,1,1],[12,0,0],[13,0,0],[14,0,0],[15,0,0],[16,10,1],[17,0,1],[18,0,0],[19,0,0]],
"ext":[0,0]}
)



###owner is hero id

game/study_mod_api.php city=92832&tech=17&owner=0

{"code":0,"ret":{"cdlist":[{"id":299380,"cdtype":2,"target":17,"owner":0,"secs":146}]}}



"""


if __name__ == "__main__":
    print Tech.COSTS
    print Tech.cost(Tech.DEFENSE_FORMATION, 1)
