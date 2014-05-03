import logging
import unittest

from emross import mail, mobs
del mobs.Unit.UNITS[:]

mobs.units = [
    mobs.Unit('Horror', mobs.DevilArmy.FIVE_STAR),
    mobs.Unit('Horror', mobs.DevilArmy.SIX_STAR),
    mobs.Unit('Nightmare', mobs.DevilArmy.SIX_STAR),
    mobs.Unit('Inferno', mobs.DevilArmy.SEVEN_STAR),
    mobs.Unit('Inferno', mobs.DevilArmy.EIGHT_STAR),
    mobs.Unit('', mobs.DevilArmy.SEVEN_STAR, alias='Inferno'),
    mobs.Unit('', mobs.DevilArmy.EIGHT_STAR, alias='Inferno'),
]
from test import bot


ENEMY_HEROES = ['ChaosLord', 'ChaosDevourer']
ENEMY_TROOPS = [
    ('Horror', 6000),
    ('Nightmare', 1000),
    ('Inferno', 0), ('', 1235)
]

logger = logging.getLogger(__name__)

class TestMail(unittest.TestCase):
    def setUp(self):
        self.bot = bot
        self.messages = [
            (True, 'ChaosLord', """<b>[Hero]<\/b><br\/>ChaosLord (Lvl.15)<br\/><br\/><b>[Troops]<\/b><br\/>Horror(5340)<br>Attack(15)&nbsp;&nbsp;Defense(8)&nbsp;&nbsp;Health(80)<br><br>"""),
            (False, 'ChaosLord', """<b>[Hero]<\/b><br\/>ChaosLord (Lvl.15)<br\/><br\/><b>[Troops]<\/b><br\/>Horror(5351)<br>Attack(15)&nbsp;&nbsp;Defense(8)&nbsp;&nbsp;Health(80)<br>Nightmare(1337)<br>Attack(15)&nbsp;&nbsp;Defense(8)&nbsp;&nbsp;Health(80)<br>"""),
            (True, 'ChaosLord', """<b>[Hero]<\/b><br\/>ChaosLord (Lvl.15)<br\/><br\/><b>[Troops]<\/b><br\/>Nightmare(1000)<br>Attack(15)&nbsp;&nbsp;Defense(8)&nbsp;&nbsp;Health(80)<br>"""),
            (False, 'ChaosLord', """<b>[Hero]<\/b><br\/>ChaosLord (Lvl.15)<br\/><br\/><b>[Troops]<\/b><br\/>Nightmare(1337)<br>Attack(15)&nbsp;&nbsp;Defense(8)&nbsp;&nbsp;Health(80)<br>"""),
            (True, 'ChaosDevourer', """<b>[Hero]<\/b><br\/>ChaosDevourer (Lvl.12)<br\/><br\/><b>[Troops]<\/b><br\/>Horror(2387)<br>Attack(15)&nbsp;&nbsp;Defense(8)&nbsp;&nbsp;Health(80)<br>"""),
            (True, 'ChaosDevourer', """<b>[Hero]<\/b><br\/>ChaosDevourer (Lvl.12)<br\/><br\/><b>[Troops]<\/b><br\/>(1234)<br>Attack(15)&nbsp;&nbsp;Defense(8)&nbsp;&nbsp;Health(80)<br>"""),
            (True, 'ChaosDevourer', """<b>[Hero]<\/b><br\/>ChaosDevourer (Lvl.12)<br\/><br\/><b>[Troops]<\/b><br/>(1234)<br>Attack(15)&nbsp;&nbsp;Defense(8)&nbsp;&nbsp;Health(80)<br>"""),

            # An unknown hero eg. in a special event
            (False, None, """<b>[Hero]<\/b><br\/>SpecialHero (Lvl.15)<br\/><br\/><b>[Troops]<\/b><br\/>Inferno(9293)<br>Attack(120)&nbsp;&nbsp;Defense(40)&nbsp;&nbsp;Health(180)<br>"""),
            (False, None, r"""<b>[Hero]</b><br/><br/><br/><b>[Troops]</b><br/>(8244)<br>Attack(120)&nbsp;&nbsp;Defense(40)&nbsp;&nbsp;Health(180)<br><br>"""),
        ]

    def test_mail_parser_types(self):
        self.assertEqual(-1, mail.AttackMailHandler(self.bot).TYPE)
        self.assertEqual(3, mail.ScoutMailHandler(self.bot).TYPE)

    def test_mail_parser(self):
        mail_parser = mail.MailParser(ENEMY_TROOPS, ENEMY_HEROES)
        logger.debug(mobs.units)

        for attackable, hero, message in self.messages:
            logger.debug((attackable, hero, message))
            troops = mail_parser.find_troops(message)
            logger.debug(troops)
            self.assertEqual(attackable, mail_parser.is_attackable(troops), 'Attackable result does not match')
            self.assertEqual(hero, mail_parser.find_hero(message))

    def test_mob_type_cache(self):
        self.assertEqual(len(mobs.Unit.UNITS), len(mobs.units))

    def test_parsing_mobs_units(self):
        mail_parser = mail.MailParser(heroes=ENEMY_HEROES)

        for attackable, hero, message in self.messages:
            logger.debug((attackable, hero, message))
            troops = mail_parser.find_troops(message)
            logger.debug(troops)
            self.assertNotEqual({}, troops)



    def test_missing_troop_name(self):
        mail_parser = mail.MailParser([('', 10000)], ENEMY_HEROES)

        message = """<b>[Hero]<\/b><br\/>ChaosDevourer (Lvl.12)<br\/><br\/><b>[Troops]<\/b><br\/>(1234)<br>Attack(15)&nbsp;&nbsp;Defense(8)&nbsp;&nbsp;Health(80)<br>"""
        troops = mail_parser.find_troops(message)
        self.assertEqual({'':1234}, troops)
        self.assertEqual(True, mail_parser.is_attackable(troops))

        unit = troops.keys()[0]
        self.assertEqual(unit, '')

        mob = mobs.Unit.find(unit, mobs.DevilArmy.EIGHT_STAR)
        self.assertEqual('Inferno', mob.name)
