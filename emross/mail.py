import logging
logger = logging.getLogger(__name__)

import re

import settings


class MailException: pass
class NoMailInInbox(MailException): pass


class Mail:
    WAR_RESULT_INFO = 'game/war_result_info_api.php'
    WAR_RESULT_LIST = 'game/war_result_list_api.php'

    def __init__(self, bot, id, data):
        self.bot = bot
        self.id = id
        self.data = data
        self.message = None
        self.processed = False

    def fetch(self):
        self.message = self.bot.api.call(self.WAR_RESULT_INFO, id=self.id)['ret']

    def delete(self):
        return self.bot.api.call(self.WAR_RESULT_LIST, action='delete', id=self.id)

    def add_fav(self, cat):
        return self.bot.favourites.add(wid=self.id, cat=cat)


class MailHandler:

    def __init__(self, bot, type):
        self.bot = bot
        self.mail = []
        self.type = type


    def list_mail(self, page=1):
        json = self.bot.api.call(Mail.WAR_RESULT_LIST, page=page, type=self.type)

        if json['ret']:
            if len(json['ret']['war']) == 0:
                raise NoMailInInbox

            for m in json['ret']['war']:
                mail = Mail(self.bot, m['id'], m)
                self.mail.append(mail)

            return json['ret']['max']
        else:
            raise MailException



    def delete_bulk(self, id):
        parts = map(None, *(iter(id),) * 10)

        for part in parts:
            ids = ','.join(str(o.id) for o in part if o is not None)
            logger.info('Deleting mail id%s %s' % ("'s" if len(part) > 1 else '', ids))
            json = self.bot.api.call(Mail.WAR_RESULT_LIST, action='delete', id=ids)


    def process(self):
        self.mail[:] = []

        page = 1
        while True:
            max = self.list_mail(page)
            logger.info('Reading page %d/%d' % (page, max))

            if max == page:
                break

            page += 1


class AttackMailHandler(MailHandler):
    def __init__(self, bot):
        MailHandler.__init__(self, bot, type=-1)


    def process(self):
        logger.info('Cleaning up war reports...')

        MailHandler.process(self)

        # Now delete the mails
        processed_mail = [m for m in self.mail if m.data['dname'] is None]

        self.delete_bulk(processed_mail)
        self.mail[:] = []

class ScoutMailHandler(MailHandler):
    def __init__(self, bot):
        MailHandler.__init__(self, bot, type=3)
        self.parser = MailParser(settings.enemy_troops)


    def process(self):
        """
        Read through all scout reports and examine the reports
        we have of any devil armies
        """
        MailHandler.process(self)


        for mail in self.mail:

            try:
                # NPC does not have a defender
                if mail.data['dname']:
                    continue

                mail.fetch()

                troops = self.parser.find_troops(mail.message['scout_report']['result'])
                if self.parser.is_attackable(troops):
                    result = 'ADDED'
                    mail.add_fav(2)
                else:
                    result = 'REJECTED'


                logger.info('%s devil army at [%d/%d] with troops %s' % (result, mail.data['dx'], mail.data['dy'],
                    ', '.join(['%s(%d)'] * len(settings.enemy_troops)) % sum(zip([s for s, c in settings.enemy_troops], troops), ())))


                mail.processed = True
            except TypeError:
                logger.info('Error parsing mail: %s\n\n%s\n\n\n%s' % (mail.data, mail.message, '*'*40))



        # Now delete the mails
        processed_mail = [m for m in self.mail if m.processed]

        self.delete_bulk(processed_mail)

        self.mail[:] = [m for m in self.mail if not m.processed]


class MailParser:
    def __init__(self, troops=()):
        self.troops = troops
        self.reTroops = []
        for troop, count in troops:
            self.reTroops.append(re.compile('%s\((\d+)\)' % troop))


    def find_troops(self, message):
        troops = []

        for reg in self.reTroops:
            t = reg.search(message)
            if t:
                count = int(t.group(1))
            else:
                count = 0

            troops.append(count)

        return troops



    def is_attackable(self, troops):
        """
        If the troop count is not exceeded for a given troop type then this target is attackable
        """
        limits = [t[1] for t in self.troops]

        return False not in [a<=b for a,b in zip(troops, limits)]






def main():
    logging.basicConfig(level=logging.DEBUG)

    mail_parser = MailParser(settings.enemy_troops)

    message = ["""<b>[Hero]<\/b><br\/>ChaosLord (Lvl.15)<br\/><br\/><b>[Troops]<\/b><br\/>Horror(5351)<br>Attack(15)&nbsp;&nbsp;Defense(8)&nbsp;&nbsp;Health(80)<br><br>""",
        """<b>[Hero]<\/b><br\/>ChaosLord (Lvl.15)<br\/><br\/><b>[Troops]<\/b><br\/>Horror(5351)<br>Attack(15)&nbsp;&nbsp;Defense(8)&nbsp;&nbsp;Health(80)<br>Nightmare(1337)<br>Attack(15)&nbsp;&nbsp;Defense(8)&nbsp;&nbsp;Health(80)<br>""",
        """<b>[Hero]<\/b><br\/>ChaosLord (Lvl.15)<br\/><br\/><b>[Troops]<\/b><br\/>Nightmare(1337)<br>Attack(15)&nbsp;&nbsp;Defense(8)&nbsp;&nbsp;Health(80)<br>""",
        """<b>[Hero]<\/b><br\/>ChaosLord (Lvl.15)<br\/><br\/><b>[Troops]<\/b><br\/>Horror(2387)<br>Attack(15)&nbsp;&nbsp;Defense(8)&nbsp;&nbsp;Health(80)<br>""",
        """<b>[Hero]<\/b><br\/>ChaosLord (Lvl.15)<br\/><br\/><b>[Troops]<\/b><br\/>Inferno(9293)<br>Attack(120)&nbsp;&nbsp;Defense(40)&nbsp;&nbsp;Health(180)<br>"""
    ]

    logger.info('Enemy troop ratio we are using: %s' % list(mail_parser.troops))

    for m in message:
        troops = mail_parser.find_troops(m)
        logger.info('Troops %s, Attackable: %s' % (troops, mail_parser.is_attackable(troops)))


if __name__ == "__main__":
    main()
