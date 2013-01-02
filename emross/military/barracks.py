from emross.api import EmrossWar

class Barracks:
    ACTION_CONFIRM_URL = 'game/armament_action_do_api.php'
    ACTION_DO_URL = 'game/armament_action_task_api.php'
    SOLDIER_EDUCATE_URL = 'game/soldier_educate_api.php'

    def __init__(self, bot, city):
        self.bot = bot
        self.city = city
        self.soldiers = []

    def get_soldiers(self):
        json = self.bot.api.call(self.SOLDIER_EDUCATE_URL, city = self.city.id)
        try:
            self.soldiers = json['ret']['soldiers']
        except TypeError:
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