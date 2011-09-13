import uuid
from helper import EmrossWarApi, EmrossWarApiException


bot = EmrossWarApi()

def register(username = None, password = None, referrer = None):
    """
    user=creative&action=reg&referer=rm9y5w&code=875628a8-ccf7-11e0-9fbd-00216b4d955c
    """
    json = bot.call('info.php', server='m.emrosswar.com', user = username, action = 'reg', referer = referrer, code = uuid.uuid4())

    print json


if __name__ == "__main__":
    try:
        register('wild', referrer = 'lordkratos')
    except EmrossWarApiException, e:
        print e
