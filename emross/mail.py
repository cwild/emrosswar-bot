import re

import settings


class MailException: pass
class NoMailInInbox(MailException): pass

class MailHandler:
    def __init__(self, api, type):
        self.api = api
        self.mail = []
        self.type = type


    def list_mail(self, page=1):
        json = self.api.call(settings.war_result_list, page=page, type=self.type)

        if json['ret']:
            if len(json['ret']['war']) == 0:
                raise NoMailInInbox

            for m in json['ret']['war']:
                mail = Mail(self.api, m['id'], m)
                self.mail.append(mail)

            return json['ret']['max']
        else:
            raise MailException



    def delete_bulk(self, id):
        parts = map(None, *(iter(id),) * 10)

        for part in parts:
            ids = ','.join(str(o.id) for o in part if o is not None)
            print 'Deleting mail id%s %s' % ("'s" if len(part) > 1 else '', ids)
            json = self.api.call(settings.war_result_list, action='delete', id=ids)


    def process(self):
        self.mail[:] = []

        page = 1
        while True:
            max = self.list_mail(page)
            print 'Reading page %d/%d' % (page, max)

            if max == page:
                break

            page += 1


class AttackMailHandler(MailHandler):
    def __init__(self, api):
        MailHandler.__init__(self, api, type=-1)


    def process(self):
        print 'Cleaning up war reports...'

        MailHandler.process(self)

        # Now delete the mails
        processed_mail = [m for m in self.mail if m.data['dname'] is None]

        self.delete_bulk(processed_mail)
        self.mail[:] = []

class ScoutMailHandler(MailHandler):
    def __init__(self, api):
        MailHandler.__init__(self, api, type=3)
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


                print '%s devil army at [%d/%d] with troops %s(%d), %s(%d)' % (result, mail.data['dx'], mail.data['dy'], settings.enemy_troops[0], troops[0], settings.enemy_troops[1], troops[1] )

                mail.processed = True
            except TypeError:
                print 'Error parsing mail: %s\n\n%s\n\n\n%s' % (mail.data, mail.message, '*'*40)



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



class Mail:
    def __init__(self, api, id, data):
        self.api = api
        self.id = id
        self.data = data
        self.message = None
        self.processed = False


    def fetch(self):
        json = self.api.call(settings.war_result_info, id=self.id)

        self.message = json['ret']


    def delete(self):
        json = self.api.call(settings.war_result_list, action='delete', id=self.id)


    def add_fav(self, cat):
        json = self.api.call(settings.api_fav, act='addreport', wid=self.id, cat=cat)














def main():
    mail_parser = MailParser(settings.enemy_troops)

    message = ["""<b>[Hero]<\/b><br\/>ChaosLord (Lvl.15)<br\/><br\/><b>[Troops]<\/b><br\/>Horror(5351)<br>Attack(15)&nbsp;&nbsp;Defense(8)&nbsp;&nbsp;Health(80)<br><br>""",
        """<b>[Hero]<\/b><br\/>ChaosLord (Lvl.15)<br\/><br\/><b>[Troops]<\/b><br\/>Horror(5351)<br>Attack(15)&nbsp;&nbsp;Defense(8)&nbsp;&nbsp;Health(80)<br>Nightmare(1337)<br>Attack(15)&nbsp;&nbsp;Defense(8)&nbsp;&nbsp;Health(80)<br>""",
        """<b>[Hero]<\/b><br\/>ChaosLord (Lvl.15)<br\/><br\/><b>[Troops]<\/b><br\/>Nightmare(1337)<br>Attack(15)&nbsp;&nbsp;Defense(8)&nbsp;&nbsp;Health(80)<br>""",
        """<b>[Hero]<\/b><br\/>ChaosLord (Lvl.15)<br\/><br\/><b>[Troops]<\/b><br\/>Horror(2387)<br>Attack(15)&nbsp;&nbsp;Defense(8)&nbsp;&nbsp;Health(80)<br>""",
        """<b>[Hero]<\/b><br\/>ChaosLord (Lvl.15)<br\/><br\/><b>[Troops]<\/b><br\/>Inferno(9293)<br>Attack(120)&nbsp;&nbsp;Defense(40)&nbsp;&nbsp;Health(180)<br>"""
    ]

    print 'Enemy troop ratio we are using: %s' % list(mail_parser.troops)

    for m in message:
        troops = mail_parser.find_troops(m)
        print 'Troops %s, Attackable: %s' % (troops, mail_parser.is_attackable(troops))

    #print 'Enemy troop ratio we are using: %d' % settings.enemy_troop_ratio
    #print 'Consider for attack: %s' % mail_parser.is_attackable(troops)


if __name__ == "__main__":
    main()
