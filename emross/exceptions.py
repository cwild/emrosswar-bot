class EmrossWarException(Exception): pass
class EmrossWarApiException(EmrossWarException): pass
class BotException(EmrossWarException): pass

class NoTargetsFound(BotException): pass
class NoTargetsAvailable(NoTargetsFound): pass

class WorldException(BotException): pass
class OutOfSpies(WorldException): pass