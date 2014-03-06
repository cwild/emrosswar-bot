from emross.api import EmrossWar
from emross.utility.task import Task


class GiftCollector(Task):
    INTERVAL = 3600*2
    ENFORCED_INTERVAL = True
    GIFT_URL = 'game/gift_api.php'

    def process(self):
        if self.bot.pvp:
            return
    
        self.log.info('Check for gifts')
        json = self.bot.api.call(self.GIFT_URL, action='list')

        if json['code'] == EmrossWar.SUCCESS:
            gifts = json['ret']
            for gift in gifts:
                self.log.debug(gift)

                if gift.get('get', False) == True:
                    json = self.bot.api.call(self.GIFT_URL, action='get', id=gift['id'])


if __name__ == '__main__':
    json = {"code":0,"ret":{"item":[{"id":0,"sid":80,"num":1},{"id":0,"sid":81,"num":1},{"id":0,"sid":163,"num":1},{"id":0,"sid":129,"num":1}],"gem":0,"wood":0,"food":0,"iron":0,"gold":0,"rumor":0,"ep":0}}
    print json
