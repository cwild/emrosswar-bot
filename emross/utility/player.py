class Player:
    def __init__(self, server, key, pushid=None, user_agent=None):
        self.server = server
        self.key = key
        self.pushid = pushid
        self.user_agent = user_agent