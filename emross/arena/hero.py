class Hero:
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

    def get_status(self):
        pass

