class EmrossWarException(Exception): pass
class EmrossWarApiException(EmrossWarException): pass
class BotException(EmrossWarException): pass

class NoTargetsFound(BotException): pass
class NoTargetsAvailable(NoTargetsFound): pass

class WorldException(BotException): pass
class OutOfSpies(EmrossWarException): pass

class InsufficientSoldiers(BotException):
    def __init__(self, troop_count = 0):
        self.troop_count = troop_count
