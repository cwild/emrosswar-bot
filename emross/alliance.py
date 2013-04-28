import logging
import time

from emross.api import EmrossWar

logger = logging.getLogger(__name__)

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


class Donator:
    UNION_INFO = 'game/api_union_info.php'

    def __init__(self, bot):
        self.bot = bot
        self.info = None

        self.hall_donation_forced = False
        self.hall_timeout = 0
        self.tech_timeout = 0

    def update(self):
        json = self.bot.api.call(self.UNION_INFO, op='info')
        self.info = json['ret']

    def donate_to_hall(self, gold, city):
        i = self.info

        if i[4] is not 0:
            self.hall_timeout = time.time() + i[4]
            return

        try:
            # Catch hall being max already
            if self.hall_donation_forced is False:
                i[1] / i[2]
            json = self.bot.api.call(self.UNION_INFO, op='donate', num=gold, city=city)
            self.hall_timeout = time.time() + json['ret'][4]
        except IndexError:
            pass
        except TypeError:
            self.hall_timeout = None


    def get_tech_info(self, techid):
        json = self.bot.api.call(self.UNION_INFO, op='techinfo', techid=techid)
        return json['ret']


    def choose_preferred_tech(self, tech_preference = []):
        techs = self.info[5]
        techs = [t for t in enumerate(techs) if t[1][0] == AllianceTechStatus.ACTIVATED and t[1][1] < 5]

        if len(techs) is 0:
            raise ValueError

        logger.info('Choosing from the following: %s' % (', '.join([EmrossWar.LANG['ALLY_TECH'][str(t[0]+1)]['name'] for t in techs])))

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
            json = self.bot.api.call(self.UNION_INFO, op='tdonate',
                                num=gold, techid=techid, city=city)

            self.tech_timeout = time.time() + json['ret'][1][4]
        except Exception:
            pass


    def make_donations(self, tech_preference = []):
        """
        Make donations to the alliance when appropriate.
        Cherry pick the favoured techs to donate to
        """

        if self.bot.userinfo['guildid'] == 0:
            logger.info('Not in an alliance. Cannot donate.')
            return False

        check_hall = self.hall_timeout is not None and self.hall_timeout <= time.time()
        check_tech = self.tech_timeout is not None and self.tech_timeout <= time.time()

        if check_hall or check_tech:
            self.update()
        else:
            return

        city = self.bot.richest_city()


        if check_tech:
            # second index is techid but they all share the same timer, so just use 0
            cooldown = self.info[5][0][2]
            if cooldown is not 0:
                logger.info('Cannot donate to tech yet. Try again in %d seconds' % cooldown)
                self.tech_timeout = time.time() + cooldown
            else:
                try:
                    techid = self.choose_preferred_tech(tech_preference)
                    amount = self.get_tech_info(techid)[2]
                    logger.info('Donate %d gold to %s' % (amount, EmrossWar.LANG['ALLY_TECH'][str(techid)]['name']))

                    self.donate_to_tech(gold=amount, techid = techid, city = city.id)
                    city.update()
                    city = self.bot.richest_city()
                except (TypeError, ValueError):
                    pass


        if check_hall:
            cooldown = self.info[4]
            if cooldown is not 0:
                logger.info('Cannot donate to hall yet. Try again in %d seconds' % cooldown)
                self.hall_timeout = time.time () + cooldown
            else:
                try:
                    if self.hall_donation_forced is False:
                        self.info[1] / self.info[2]
                    amount = self.info[3]
                    logger.info('Donate %d gold to Hall of Alliance' % amount)
                    self.donate_to_hall(gold=amount, city = city.id)
                except TypeError:
                    logger.info('Hall of Alliance is already complete')
                    self.hall_timeout = None
