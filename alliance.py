import time

class AllianceTechStatus:
    ACTIVATED = 0
    NOT_ACTIVATED = 1
    LOCKED = 2
    NOT_READY = 3

class Alliance:
    CIVILIZATION = 1
    VETERAN = 2
    SILOS = 3
    DILIGENCE = 4
    VALOR = 5
    TENACITY = 6
    VAULT = 7
    STONECRAFT = 8
    PEDAGOGICS = 9
    PROPAGANDA = 10
    INCENTIVE = 11
    TOUGHNESS = 12
    THRIFTY = 13
    DISCIPLINE = 14
    CAMPING = 15
    INSPIRATION = 16
    BATTLECRY = 17
    LOGISTICS = 18
    BLOODFLAG = 19
    MILICADEMY = 20

    TECH = {
        1:  'Civilisation',
        2:  'Veteran',
        3:  'Silos',
        4:  'Diligence',
        5:  'Valor',
        6:  'Tenacity',
        7:  'Vault',
        8:  'Stonecraft',
        9:  'Pedagogics',
        10: 'Propaganda',
        11: 'Incentive',
        12: 'Toughness',
        13: 'Thrifty',
        14: 'Discipline',
        15: 'Camping',
        16: 'Inspiration',
        17: 'Battlecry',
        18: 'Logistics',
        19: 'Bloodflag',
        20: 'Milicademy'
    }


class Donator:
    UNION_INFO = 'game/api_union_info.php'

    def __init__(self, api, bot):
        self.api = api
        self.bot = bot
        self.info = None

        self.hall_timeout = 0
        self.tech_timeout = 0

    def update(self):
        json = self.api.call(Donator.UNION_INFO, op='info')
        self.info = json['ret']

    def donate_to_hall(self, gold, city):
        i = self.info

        if i[4] is not 0:
            self.hall_timeout = time.time() + i[4]
            return

        try:
            # Catch hall being max already
            i[1] / i[2]
            json = self.api.call(Donator.UNION_INFO, op='donate', num=gold, city=city)
            self.hall_timeout = time.time() + json['ret'][4]
        except IndexError:
            pass
        except TypeError:
            self.hall_timeout = None


    def get_tech_info(self, techid):
        json = self.api.call(Donator.UNION_INFO, op='techinfo', techid=techid)
        return json['ret']


    def choose_preferred_tech(self, tech_preference = []):
        techs = self.info[5]
        techs = [t for t in enumerate(techs) if t[1][0] == AllianceTechStatus.ACTIVATED and t[1][1] < 5]

        if len(techs) is 0:
            raise ValueError

        print 'Choosing from the following: %s' % (', '.join([Alliance.TECH[t[0]+1] for t in techs]))

        try:
            # Get all the tech IDs
            ids = [1 + id[0] for id in techs]
            tech = None

            """
            FIFO, start checking at the end of preferences and work towards the
            beginning to choose the optimal choice
            """
            for t in reversed(tech_preference):
                if t in ids:
                    tech = t

            # Simple check to ensure tech is an int
            tech/tech
        except (IndexError, TypeError):
            return techs[0][0] + 1

        return tech

    def donate_to_tech(self, gold, techid, city):
        try:
            json = self.api.call('game/api_union_info.php', op='tdonate',
                                num=gold, techid=techid, city=city)

            self.tech_timeout = time.time() + json['ret'][5][techid-1][2]
        except Exception:
            pass


    def make_donations(self, tech_preference = []):
        """
        Make donations to the alliance when appropriate.
        Cherry pick the favoured techs to donate to
        """

        if (self.hall_timeout is not None != self.hall_timeout <= time.time()) and \
            (self.tech_timeout is not None != self.tech_timeout <= time.time()):
            self.update()
        else:
            return

        city = None

        if self.hall_timeout is not None:
            try:
                self.info[1] / self.info[2]
                print 'Donate to Hall of Alliance'
                city = self.bot.richest_city(city)
                self.donate_to_hall(gold=self.info[3], city = city.id)
            except TypeError:
                print 'Hall of Alliance is already complete'
                self.hall_timeout = None


        if self.tech_timeout is not None:
            if self.info[5][0][2] is not 0:
                """ Can't donate next until current time + wait time """
                self.tech_timeout = time.time() + self.info[5][0][2]
            else:
                try:
                    techid = self.choose_preferred_tech(tech_preference)
                    amount = self.get_tech_info(techid)[2]
                    print 'Donate %d gold to %s' % (amount, Alliance.TECH[techid])

                    city = self.bot.richest_city(city)
                    self.donate_to_tech(gold=amount, techid = techid, city = city.id)
                except (TypeError, ValueError), e:
                    pass
