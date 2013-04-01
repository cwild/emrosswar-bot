from emross.api import EmrossWar
from emross.resources import Resource

import logging
logger = logging.getLogger(__name__)

class Barracks(object):
    ACTION_CONFIRM_URL = 'game/armament_action_do_api.php'
    ACTION_DO_URL = 'game/armament_action_task_api.php'
    SOLDIER_EDUCATE_URL = 'game/soldier_educate_api.php'

    LOOT = 0
    TRANSPORT = 2
    SCOUT = 3
    BUILD = 5
    ATTACK = 7
    OCCUPY = 8
    CONQUER = 9

    TRAINING_LIST_FULL = 2310

    PROTECT_CASTLE = 1
    DO_NOT_ENGAGE = 2
    DO_NOT_ENGAGED_IF_OUTNUMBERED = 3

    def __init__(self, bot, city):
        self.bot = bot
        self.city = city
        self.soldiers = []
        super(Barracks, self).__init__()

    def camp_info(self):
        """
        {'code': 0, 'ret': {'head': 17922, 'f': -372749, 'space': 1877, 'next': [0, 0],
        'soldiers': [
            [1, 0, True], [2, 29, True], [3, 0, True], [4, 0, True], [5, 0, True],
            [6, 0, True], [7, 0, True], [8, 3424, True], [9, 0, True], [10, 0, True],
            [11, 0, True], [12, 0, True], [13, 0, True], [14, 2426, True],
            [15, 126, True], [16, 0, True], [17, 7163, True], [18, 200, True]],
        'def': 2}}
        """
        json = self.bot.api.call(self.SOLDIER_EDUCATE_URL, city = self.city.id)
        try:
            self.soldiers[:] = json['ret']['soldiers']
        except TypeError:
            pass

        return json

    get_soldiers = camp_info

    def train_troops(self, soldier, quantity, hero=0):
        """
        city=64507&action=soldier_educate&soldier=8&num=438&gen=2
        {"code":0,"ret":{"cdlist":[{"id":540999,"cdtype":3,"target":8,"owner":0,"secs":20}]}}
        """
        json = self.bot.api.call(self.SOLDIER_EDUCATE_URL, action='soldier_educate', city=self.city.id, soldier=soldier, num=quantity, gen=hero)

        if json['code'] == EmrossWar.SUCCESS:
            logger.info('Train %d troops of type %d at city "%s"' % (quantity, soldier, self.city.name))

        return json

    def defense_strategy(self, strategy=DO_NOT_ENGAGE):
        """
        action=def&city=12345&defense=3
        """
        self.bot.api.call(self.SOLDIER_EDUCATE_URL, action='def', city=self.city.id, defense=strategy)

    def transport(self):
        """
        game/armament_action_do_api.php city=12456&action=do_war&attack_type=2&area=181&area_x=200&soldier_num8=1
        {"code":0,"ret":{"carry":24750,"cost_food":1800,"cost_wood":0,"cost_iron":0,"cost_gold":0,"distance":2160,"travel_sec":300}}

        game/armament_action_task_api.php take_num=24750&travel_sec=300&distance=2160&action_woods=0&action_irons=0&action_golds=0&rices=1&woods=3&irons=4&golds=2&city=12345&action=war_task&attack_type=2&area=181&area_x=200&soldier_num8=1
        {"code":0,"ret":{"cd":[{"id":98765,"cdtype":4,"target":2,"owner":0,"secs":300,"ret":0,"ext":"181\/200"}]}
        """
        pass

    def war_room(self):
        """
        bot.api.call('game/armament_action_do_api.php', act='warinfo', city=92832)
        {'code': 0, 'ret': [
            [[6035223, 5, 7, 134, '17/47', [15], [600], 17],
            [6035225, 5, 7, 143, '17/47', [15], [600], 30],
            [6035227, 5, 7, 150, '17/47', [15], [600], 172]],
        13]}
        """
        json = self.bot.api.call(self.ACTION_CONFIRM_URL, act='warinfo', city=self.city.id)
        return json

    def total_troops(self):
        troop_tally = {}

        info = self.camp_info()
        for soldier, qty, unlocked in self.soldiers:
            troop_tally[soldier] = qty

        away = self.war_room()
        for troop in away['ret'][0]:
            for soldier, qty in zip(troop[5], troop[6]):
                try:
                    troop_tally[soldier] += qty
                except KeyError:
                    troop_tally[soldier] = qty

        return troop_tally, info

    def can_train(self, troop):
        try:
            troop_id, qty, unlocked = self.soldiers[troop-1]
            return unlocked is True
        except (IndexError, TypeError):
            return False

    def confirm_and_do(self, params, sleep_confirm=(), sleep_do=(), **kwargs):
        json = self._action_confirm(params, sleep=sleep_confirm, **kwargs)

        if json['code'] == EmrossWar.SUCCESS:
            params.update(json['ret'])
            return self._action_do(params, sleep=sleep_do, **kwargs)
        else:
            logger.info(EmrossWar.LANG['ERROR']['SERVER'][str(json['code'])])

    def _action_confirm(self, params, **kwargs):
        """
        We need to confirm that we wish to perform this action.
        Shows the cost of performing the action both in resources and time

        city=12553&action=do_war&attack_type=7&gen=22&area=110&area_x=258&soldier_num15=600
        {"code":0,"ret":{"carry":820800,"cost_food":108000,"cost_wood":0,"cost_iron":0,"cost_gold":0,"distance":6720,"travel_sec":120}}
        """
        kwargs.update(params)
        return self.bot.api.call(self.ACTION_CONFIRM_URL, city=self.city.id, **kwargs)


    def _action_do(self, params, **kwargs):
        """
        city=12553&action=war_task&attack_type=7&gen=22&area=110&area_x=258&soldier_num15=600
        carry=820800&cost_food=108000&cost_wood=0&cost_iron=0&cost_gold=0&distance=6720&travel_sec=120
        """

        try:
            current_food = self.city.resource_manager.get_amount_of(Resource.FOOD)
            if params['cost_food'] > current_food:
                self.city.replenish_food(params['cost_food']-current_food)
        except KeyError as e:
            logger.exception(e)

        kwargs.update(params)
        json = self.bot.api.call(self.ACTION_DO_URL, city=self.city.id, **kwargs)

        if json['code'] == EmrossWar.SUCCESS:
            soldiers = [(k.replace('soldier_num', ''), v) for k, v in params.iteritems() if k.startswith('soldier_num')]

            for k, v in soldiers:
                i = int(k)
                soldier = [s for s in self.soldiers if i == s[0]][0]
                soldier[1] -= v

            for k, v in kwargs.iteritems():
                if k.startswith('cost_'):
                    try:
                        res = k[5] # w,i,f,g
                        cur = self.city.resource_manager.get_amount_of(res)
                        self.city.resource_manager.set_amount_of(res, cur-int(v))
                    except KeyError:
                        pass

        return json

if __name__ == "__main__":
    from emross.military.camp import Soldier
    from bot import bot
    bot.update()

    for city in bot.cities:
        city.barracks.camp_info()
        print city.barracks.can_train(Soldier.ASSASSIN)
