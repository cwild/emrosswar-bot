class EmrossWarException(Exception): pass
class EmrossWarApiException(EmrossWarException): pass
class BotException(EmrossWarException): pass

class TargetException(BotException): pass
class NoTargetsFound(TargetException): pass
class NoTargetsAvailable(TargetException): pass

class WorldException(BotException): pass
class OutOfSpies(EmrossWarException): pass

class InsufficientHeroCommand(BotException): pass
class InsufficientSoldiers(BotException): pass

class TradeException(BotException): pass
