class EmrossWarException(Exception): pass
class EmrossWarApiException(EmrossWarException): pass
class BotException(EmrossWarException): pass

class TargetException(BotException): pass
class NoTargetsFound(TargetException): pass
class NoTargetsAvailable(TargetException): pass

class WorldException(BotException): pass
class OutOfSpies(EmrossWarException): pass

class InsufficientHeroCommand(BotException): pass
class InsufficientSoldiers(BotException):
    def __init__(self, troop_count = 0):
        self.troop_count = troop_count

class TradeException(BotException): pass
