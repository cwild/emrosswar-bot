import time

from emross.alliance import Alliance
from emross.api import EmrossWar
from emross.utility.task import Task

class AllianceTechStatus:
    ACTIVATED = 0
    NOT_ACTIVATED = 1
    LOCKED = 2
    NOT_READY = 3

class Donator(Task):
    """
    Make donations to the alliance when appropriate.
    Cherry pick the favoured techs to donate to
    """

    def __init__(self, bot):
        super(Donator, self).__init__(bot)
        self.hall_timeout = 0
        self.tech_timeout = 0

    def process(self, tech_preference=[], force_hall_donation=False,
                pvp_donate=False, interval=900, *args, **kwargs):

        if not self.bot.alliance.in_ally:
            self.sleep(30)
            return True

        if self.bot.pvp and pvp_donate:
            self.sleep(86400)
            return True

        check_hall = self.hall_timeout is not None and self.hall_timeout <= time.time()
        check_tech = self.tech_timeout is not None and self.tech_timeout <= time.time()

        if check_hall or check_tech:
            self.bot.alliance.update()
        else:
            return True

        city = self.bot.richest_city()

        if check_tech:
            # second index is techid but they all share the same timer, so just use 0
            cooldown = self.bot.alliance.hall_tech[0][2]
            if cooldown is not 0:
                self.log.info('Cannot donate to any "{0}" yet. Try again in {1} seconds'.format(
                    EmrossWar.TRANSLATE.get('f_ally')['35'],
                    cooldown)
                )
                self.tech_timeout = time.time() + cooldown
            else:
                try:
                    techid = self.choose_preferred_tech(tech_preference)
                    amount = self.get_tech_info(techid)[2]
                    self.log.info('{donate} {amount} {currency} to {tech} from "{city}"'.format(
                        donate=EmrossWar.TRANSLATE.get('f_ally')['34'],
                        amount=amount,
                        currency=EmrossWar.LANG.get('COIN', 'gold'),
                        tech=EmrossWar.LANG['ALLY_TECH'][str(techid)]['name'],
                        city=city.name
                        )
                    )

                    self.donate_to_tech(gold=amount, techid=techid, city=city.id)
                    city.update()
                    city = self.bot.richest_city()
                except (TypeError, ValueError):
                    pass


        if check_hall:
            hall_name = EmrossWar.TRANSLATE.get('f_ally')['31']
            cooldown = self.bot.alliance.info[4]
            if cooldown is not 0:
                self.log.info('Cannot donate to {0} yet. Try again in {1} seconds'.format(
                    hall_name, cooldown))
                self.hall_timeout = time.time() + cooldown
            else:
                try:
                    if force_hall_donation is False:
                        self.bot.alliance.info[1] / self.bot.alliance.info[2]
                    amount = self.bot.alliance.info[3]
                    self.log.info('{donate} {amount} {currency} to {hall} from "{city}"'.format(
                        donate=EmrossWar.TRANSLATE.get('f_ally')['34'],
                        amount=amount,
                        currency=EmrossWar.LANG.get('COIN', 'gold'),
                        hall=hall_name, city=city.name)
                    )
                    self.donate_to_hall(gold=amount, city=city.id)
                except TypeError:
                    self.log.info('{0} is already complete'.format(hall_name))
                    self.hall_timeout = None


        delays = []
        for timer in [self.hall_timeout, self.tech_timeout]:
            if timer and timer > 0:
                delays.append(time.time()-timer)

        try:
            self.sleep(min(delays))
        except ValueError:
            self.sleep(interval)

    def donate_to_hall(self, gold, city):
        i = self.bot.alliance.info

        if i[4] is not 0:
            self.hall_timeout = time.time() + i[4]
            return

        try:
            json = self.bot.api.call(self.bot.alliance.UNION_INFO, op='donate', num=gold, city=city)
            if json['code'] == EmrossWar.SUCCESS:
                self.hall_timeout = time.time() + json['ret'][4]
                self.bot.alliance._info = json['ret']
        except IndexError:
            pass
        except TypeError:
            self.hall_timeout = None


    def get_tech_info(self, techid):
        json = self.bot.api.call(self.bot.alliance.UNION_INFO, op='techinfo', techid=techid)
        return json['ret']


    def choose_preferred_tech(self, tech_preference=[]):

        techs = [i for i, tech in enumerate(self.bot.alliance.hall_tech)
                    if tech[0] == AllianceTechStatus.ACTIVATED and \
                    tech[1] < Alliance.MAX_TECH_LEVEL]

        if len(techs) is 0:
            raise ValueError

        self.log.info('Choosing from the following: {0}'.format(
            ', '.join([EmrossWar.LANG['ALLY_TECH'][str(t+1)]['name'] for t in techs]))
        )

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
            return techs[0] + 1

        return tech

    def donate_to_tech(self, gold, techid, city):
        try:
            json = self.bot.api.call(self.bot.alliance.UNION_INFO, op='tdonate',
                                num=gold, techid=techid, city=city)

            self.tech_timeout = time.time() + json['ret'][1][4]
        except Exception:
            pass
