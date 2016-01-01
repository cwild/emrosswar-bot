import emross
from emross.api import EmrossWar
from emross.utility.controllable import Controllable
from emross.utility.task import Task


class GiftCollector(Task, Controllable):
    COMMAND = 'gift'
    INTERVAL = 3600*2
    ENFORCED_INTERVAL = True
    GIFT_URL = 'game/gift_api.php'
    MASTER_GIFT_URL = 'gift.php'

    @emross.defer.inlineCallbacks
    def action_collect(self, event, code, *args, **kwargs):
        """
        Retrieve a gift `code`
        """
        yield self.bot.api.call(self.MASTER_GIFT_URL, server=emross.master, \
            user=self.bot.api.player.username, code=code, **kwargs)

    @emross.defer.inlineCallbacks
    def process(self):
        if self.bot.pvp:
            emross.defer.succeed(None)
    
        self.log.info('Check for gifts')
        json = yield self.bot.api.call(self.GIFT_URL, action='list')

        if json['code'] == EmrossWar.SUCCESS:
            gifts = json['ret']
            for gift in gifts:
                self.log.debug(gift)

                if gift.get('get', False) == True:
                    json = yield self.bot.api.call(self.GIFT_URL, action='get', id=gift['id'])


if __name__ == '__main__':
    json = {"code":0,"ret":{"item":[{"id":0,"sid":80,"num":1},{"id":0,"sid":81,"num":1},{"id":0,"sid":163,"num":1},{"id":0,"sid":129,"num":1}],"gem":0,"wood":0,"food":0,"iron":0,"gold":0,"rumor":0,"ep":0}}
    print json
