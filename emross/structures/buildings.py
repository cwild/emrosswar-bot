from emross.utility.task import CostCalculator

class Building(CostCalculator):
    """
    Each structure has the following:
        - (build_type, city.data[offset])
    """
    ARENA = 10
    BARRACKS = 8
    FACILITY_CENTER = 13
    FARM = 4
    GOLD_MINE = 3
    HOUSE = 5
    IRON_MINE = 2
    SAWMILL = 1
    STORAGE = 11
    UNIVERSITY = 9
    WALL = 12


    OFFSET = {
        ARENA: 19,
        BARRACKS: 17,
        FACILITY_CENTER: 22,
        FARM: 15,
        GOLD_MINE: 14,
        HOUSE: 16,
        IRON_MINE: 13,
        SAWMILL: 12,
        STORAGE: 20,
        UNIVERSITY: 18,
        WALL: 21
    }

    COST_MODIFIER = 0.4
    COSTS = {
        ARENA: {
                "g": 1500,
                "w": 2000,
                "f": 2000,
                "i": 2000,
                "t": 93,
                "v": 0
            },
        BARRACKS: {
                "g": 200,
                "w": 300,
                "f": 150,
                "i": 200,
                "t": 32,
                "v": 0
            },
        FACILITY_CENTER: {
                "g": 1500,
                "w": 2000,
                "f": 2000,
                "i": 2000,
                "t": 73,
                "v": 0
            },
        FARM: {
                "g": 10,
                "w": 50,
                "f": 0,
                "i": 0,
                "t": 18,
                "v": 0
            },
        GOLD_MINE: {
                "g": 50,
                "w": 200,
                "f": 0,
                "i": 150,
                "t": 23,
                "v": 0
            },
        HOUSE: {
                "g": 35,
                "w": 220,
                "f": 80,
                "i": 0,
                "t": 20,
                "v": 0
            },
        IRON_MINE: {
                "g": 13,
                "w": 0,
                "f": 0,
                "i": 35,
                "t": 14,
                "v": 0
            },
        SAWMILL: {
                "g": 10,
                "w": 40,
                "f": 0,
                "i": 0,
                "t": 14,
                "v": 0
            },
        STORAGE: {
                "g": 300,
                "w": 30000,
                "f": 300,
                "i": 30000,
                "t": 540,
                "v": 0
            },
        UNIVERSITY: {
                "g": 1500,
                "w": 3500,
                "f": 1500,
                "i": 2500,
                "t": 68,
                "v": 0
            },
        WALL: {
                "g": 1000,
                "w": 0,
                "f": 1000,
                "i": 5000,
                "t": 840,
                "v": 0
            }
    }



if __name__ == "__main__":
    print Building.COSTS
    print Building.cost(Building.WALL, 5)