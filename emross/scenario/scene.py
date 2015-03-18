from emross.api import EmrossWar
from emross.exceptions import InsufficientSoldiers
from emross.utility.base import EmrossBaseObject

class Scenario(EmrossBaseObject):
    RUINED_CRYPT = 0
    FIERY_ABYSS = 1
    LAVA_PITS = 2
    FROZEN_KEEP = 3
    GLOOMY_CANYON = 4
    PILGRIMS_WAY = 5
    DEEPER_LABYRINTH = 6
    PHILIA_MINES = 7
    ELMOONII_WOODS = 8
    ROSTER_BOG = 9
    TWILIGHT_FOREST = 10

    NORMAL_MODE = 0
    HARD_MODE = 1

    ADD_SOLDIER_URL = 'game/fb_add_soldier.php'
    ATTACK_URL = 'game/fb_attack.php'
    LIST_URL = 'game/fb_list.php'
    LOTTERY_URL = 'game/fb_lottery.php'
    MOVE_URL = 'game/fb_move.php'
    OUT_URL = 'game/fb_out.php'
    START_URL = 'game/fb_start.php'

    SCENARIO_FINISHED = 9013
    SCENARIO_EXPIRED = 9014
    SCENARIO_OCCUPIED_ALREADY = 9015

    def __init__(self, *args, **kwargs):
        super(Scenario, self).__init__(*args, **kwargs)
        self.current = None
        self.highest = -1

    def attack(self, gen, pos):
        """
        fb_attack.php?gen=4&pos=4

        {
            "code": 0,
            "ret": {
                "war_report": {
                    "attacker": "playername[123:234]",
                    "defencer": "FbArmy[0]",
                    "a_gen": {
                        "gid": "222",
                        "name": "222",
                        "level": 26,
                        "attack": 312,
                        "intelligence": 124,
                        "defence": 79,
                        "loyalty": 100
                    },
                    "d_gen": {
                        "gid": "0",
                        "name": "0",
                        "level": 0,
                        "attack": 0,
                        "intelligence": 0,
                        "defence": 0,
                        "loyalty": 0
                    },
                    "war_process": [{
                        "turn": 1,
                        "aarmy": "Lonufal(1300) Kahkleh(1282) ",
                        "aattack_point": "9361900",
                        "adefence_point": "10508862",
                        "darmy": "Frost Troll(4200) ",
                        "dattack_point": "436800",
                        "ddefence_point": "462000"
                    }, {
                        "turn": 2,
                        "aarmy": "Lonufal(1300) Kahkleh(1282) ",
                        "aattack_point": "9361900",
                        "adefence_point": "10508862",
                        "darmy": "",
                        "dattack_point": "0",
                        "ddefence_point": "0"
                    }],
                    "war_result": {
                        "aflag": "1",
                        "awall_loss": 0,
                        "dwall_loss": 0,
                        "agen_status": "0",
                        "dgen_status": "0",
                        "aarmy_loss": "Lonufal(0) Kahkleh(0) ",
                        "darmy_loss": "Frost Troll(4200) ",
                        "resource": "",
                        "agen_exp": "15750",
                        "aplayer_exp": "4300",
                        "dgen_exp": null,
                        "dplayer_exp": null
                    }
                },
                "scout_report": null,
                "other_report": null
            }
        }
        """
        return self.bot.api.call(self.ATTACK_URL, gen=gen, pos=pos)


    def list(self):
        """
        {"code":0,"ret":{"add_times":1,"times":3,"max_times":3,"highest_fb":"7","hasLottery":false}

        {
            "code": 0,
            "ret": {
                "fb_label": "3",
                "army_data": {
                    "4": {
                        "soldier": {
                            "8": 1400,
                            "17": 1644
                        },
                        "pos": 0,
                        "action_time": 0,
                        "hero": "4",
                        "cd": -1351972930
                    },
                    "222": {
                        "soldier": {
                            "8": 1300,
                            "17": 1282
                        },
                        "pos": 0,
                        "action_time": 0,
                        "hero": "222",
                        "cd": -1351972930
                    }
                },
                "status": [],
                "remaining_time": 3599,
                "finish": "0"
            }
        }
        """
        return self.bot.api.call(self.LIST_URL)


    def move(self, pos):
        """
        game/fb_move.php?pos=1
        {
            "code": 0,
            "ret": {
                "soldier": {
                    "4": {
                        "soldier": {
                            "8": 1400,
                            "17": 1644
                        },
                        "pos": 0,
                        "action_time": 0,
                        "hero": "4",
                        "add_soldier": 0,
                        "cd": -1351972945
                    },
                    "222": {
                        "soldier": {
                            "8": 1300,
                            "17": 1282
                        },
                        "pos": "1",
                        "action_time": 1351973121,
                        "hero": "222",
                        "add_soldier": 0,
                        "cd": 176
                    }
                },
                "npc_data": {
                    "hero": 0,
                    "soldier": {
                        "jy_shizhang": 4200
                    }
                }
            }
        }
        """
        return self.bot.api.call(self.MOVE_URL, pos=pos)

    def lottery_wheel(self, action='list'):
        return self.bot.api.call(self.LOTTERY_URL, action=action)

    def restock(self, gen):
        """
        game/fb_add_soldier.php?gen=4
        """
        return self.bot.api.call(self.ADD_SOLDIER_URL, gen=gen)

    def start(self, city, scenario, armies, mode=NORMAL_MODE):
        """
        game/fb_start.php?
        city=123456
        fb=3
        gen=4|222
        soldier_num8=1400|1300
        soldier_num15=0|1
        soldier_num16=10|0
        soldier_num17=1644|1282
        ---
        {"code":0,"ret":{"times":2}}
        """
        gen = '|'.join([str(army['hero']) for army in armies])

        troops = {}

        for pos, army in enumerate(armies):
            for troop, qty in army['troops']:
                if not troop in troops:
                    troops[troop] = [0 for i in range(len(armies))]

                troops[troop][pos] = qty

        for troop, vals in troops.iteritems():
            soldier, total = int(troop), sum(vals)
            avail = city.barracks.soldiers[soldier-1][1]

            if avail < total:
                raise InsufficientSoldiers('"{0}" does not have enough of soldier {1} (needed={2}, available={3})'.format(\
                        city.name, soldier, total, avail))


        soldiers = dict(("soldier_num{0}".format(key), "|".join([str(v) for v in val])) for key, val in troops.iteritems())

        json = self.bot.api.call(self.START_URL, city=city.id, fb=scenario, fb_mode=mode, gen=gen, **soldiers)

        if json['code'] == EmrossWar.SUCCESS:
            self.current = scenario
            return True

        return False

    def finish(self):
        """
        Finish the Scenario by spinning the wheel
        """
        try:
            json = self.bot.api.call(self.OUT_URL)
            self.log.info('Total EP: {0}'.format(json['ret']['pvp']))
        except TypeError:
            self.log.info('Unable to obtain EP total')
            self.log.debug(json)

        json = self.list()
        self.log.info('Remaining scenario attempts: {0}'.format(json['ret']['times']))

        if json['ret']['hasLottery']:
            self.lottery_wheel(action='list')
            self.lottery_wheel(action='rotate')
