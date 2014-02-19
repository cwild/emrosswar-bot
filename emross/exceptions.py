class EmrossWarException(Exception): pass
class EmrossWarApiException(EmrossWarException): pass
class BotException(EmrossWarException): pass

class TargetException(BotException): pass
class NoTargetsFound(TargetException): pass
class NoTargetsAvailable(TargetException): pass

class WorldException(BotException): pass
class OutOfSpies(EmrossWarException): pass

class NoHeroesAvailable(BotException): pass
class InsufficientHeroCommand(BotException): pass
class InsufficientSoldiers(BotException): pass

class ResourceException(BotException): pass
class TradeException(BotException): pass

class DelayTaskProcessing(BotException):
    def __init__(self, message, delay=None):
        super(DelayTaskProcessing, self).__init__(message)
        self.delay = delay
