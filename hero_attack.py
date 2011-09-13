import settings
from helper import EmrossWarApi, EmrossWarApiException

bot = EmrossWarApi()

def attack(gid, tgid):
    """
    user=creative&action=reg&referer=rm9y5w&code=875628a8-ccf7-11e0-9fbd-00216b4d955c
    """
    json = bot.call(settings.hero_conscribe, gid=gid, tgid=tgid)

    print json

if __name__ == "__main__":
    attack(11107, 7070)
