from emross.api import EmrossWar
from emross.utility.task import Task


class GiftEvents(Task):
    INTERVAL = 3600
    ACTIVITY_URL = 'game/api_interior_activity.php'

    def process(self):
        if self.bot.userinfo['logintrack'] == 0:
            return
    
        self.log.info('Check for in-game events')
        city = self.bot.cities[0]

        collected = True

        while collected:
            collected = False
            json = self.bot.api.call(self.ACTIVITY_URL, action='list', city=city.id)

            if json['code'] != EmrossWar.SUCCESS:
                break

            for event in json['ret']:
                event_id, collectable = map(int, event[:2])

                if collectable:
                    self.log.info('Collect reward for "{0}"'.format(EmrossWar.safe_text(event[7])))

                    json = self.bot.api.call(self.ACTIVITY_URL, action='reward', city=city.id, actid=event_id)
                    if json['code'] != EmrossWar.SUCCESS:
                        collected = True


"""
Examples:
['1', '1', 0, 0, ['74', '10'], 0, 'img/item/168.png', 'level gift package', 'Reward for reaching a specific Lvl. Click picture to get more details.<br> current level 74/10', "<font color='yellow'>lv10</font> will be rewarded with 50000golds and fast buildingII*1<br/><font color='yellow'>lv20</font> (100000gold and fast trainingII*1)<br/><font color='yellow'>lv30</font> (100000gold and fast trainingII*1)<br/><font color='yellow'>lv40</font> (400000gold and gold chest*1) <br/><font color='yellow'>lv50</font> (fast buildingII*2,fast trainingII*2,fast researchII*2 and gold chest*2)"]
['2', '1', 0, 0, ['63', '7'], 0, 'img/item/168.png', 'consecutive login gift package', 'Reward for 7-consecutive-day login. Click picture to get more details.<br> consecutive login 63/7', 'login for 7 consecutive days will be rewarded with a bless of building I and a fast healing I']
['3', '0', 0, 0, ['0', '0'], 0, 'img/item/168.png', 'first recharge', 'First recharge will be rewarded. Click picture to get more details.<br> first recharge limitation 0/0', '100 first-recharge for 10 extra gems<br/>250 first-recharge for 25 extra gems<br/>550 first-recharge for 55 extra gems<br/>1500 first-recharge for 400 extra gems<br/>3200 first-recharge for 1000 extra gems']
['4', '0', 0, 0, ['0', '1000'], 0, 'img/item/168.png', 'accumulative recharge gift package', 'Reward for recharges accumulated to specific amount. Click picture to get more details.<br> recharge limitation0/1000', '1000 accumulative recharge for a random K hero(if got all K heroes, a random Rare gear instead)<br/>5000 accumulative recharges for a super gear<br/>10000 accumulative recharges for two super gears']
"""
