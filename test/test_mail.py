import unittest

from emross import mail

ENEMY_TROOPS = (('Horror', 6000), ('Nightmare', 0), ('Inferno', 0))

class TestMail(unittest.TestCase):
    def setUp(self):
        from bot import bot
        self.bot = bot

    def test_mail_parser_types(self):
        self.assertEqual(-1, mail.AttackMailHandler(self.bot).TYPE)
        self.assertEqual(3, mail.ScoutMailHandler(self.bot).TYPE)

    def test_mail_parser(self):
        mail_parser = mail.MailParser(ENEMY_TROOPS)

        messages = [
            (True, """<b>[Hero]<\/b><br\/>ChaosLord (Lvl.15)<br\/><br\/><b>[Troops]<\/b><br\/>Horror(5351)<br>Attack(15)&nbsp;&nbsp;Defense(8)&nbsp;&nbsp;Health(80)<br><br>"""),
            (False, """<b>[Hero]<\/b><br\/>ChaosLord (Lvl.15)<br\/><br\/><b>[Troops]<\/b><br\/>Horror(5351)<br>Attack(15)&nbsp;&nbsp;Defense(8)&nbsp;&nbsp;Health(80)<br>Nightmare(1337)<br>Attack(15)&nbsp;&nbsp;Defense(8)&nbsp;&nbsp;Health(80)<br>"""),
            (False, """<b>[Hero]<\/b><br\/>ChaosLord (Lvl.15)<br\/><br\/><b>[Troops]<\/b><br\/>Nightmare(1337)<br>Attack(15)&nbsp;&nbsp;Defense(8)&nbsp;&nbsp;Health(80)<br>"""),
            (True, """<b>[Hero]<\/b><br\/>ChaosLord (Lvl.15)<br\/><br\/><b>[Troops]<\/b><br\/>Horror(2387)<br>Attack(15)&nbsp;&nbsp;Defense(8)&nbsp;&nbsp;Health(80)<br>"""),
            (False, """<b>[Hero]<\/b><br\/>ChaosLord (Lvl.15)<br\/><br\/><b>[Troops]<\/b><br\/>Inferno(9293)<br>Attack(120)&nbsp;&nbsp;Defense(40)&nbsp;&nbsp;Health(180)<br>""")
        ]

        for expected, message in messages:
            troops = mail_parser.find_troops(message)
            self.assertEqual(expected, mail_parser.is_attackable(troops))
