class DevilArmy:
    ONE_STAR = 6
    TWO_STAR = 5
    THREE_STAR = 4
    FOUR_STAR = 3
    FIVE_STAR = 2
    SIX_STAR = 1
    SEVEN_STAR = 7
    EIGHT_STAR = 8


class NPC(object):
    def __init__(self, data):
        #[[14785,115,248,1,3]
        # Seems that x,y are back to front
        self._data = data
        self.id = data[0]
        self.x = data[2]
        self.y = data[1]
        self.rating = data[3]
        self.attack = data[4]

