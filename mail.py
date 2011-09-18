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





class AttackMailHandler(MailHandler):
    def __init__(self, api):
        MailHandler.__init__(self, api, type=-1)


class ScoutMailHandler(MailHandler):
    def __init__(self, api):
        MailHandler.__init__(self, api, type=3)
        self.parser = MailParser(settings.enemy_troops[0], settings.enemy_troops[1])


    def process(self):
        """
        Read through all scout reports and examine the reports
        we have of any devil armies
        """
        page = 1
        while True:
            print 'Process page %d' % page
            max = self.list_mail(page)

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

            if max == page:
                break

            page += 1


        # Now delete the mails
        processed_mail = [m for m in self.mail if m.processed]
        for mail in processed_mail:
            mail.delete()

        self.mail[:] = [m for m in self.mail if not m.processed]


class MailParser:
    def __init__(self, troop1, troop2):
        #self.reTroops = re.compile('(?:%s\((\d+)\))?.*(?:%s\((\d+)\))?' % (troops[0], troops[1]))
        self.reTroop1 = re.compile('%s\((\d+)\)' % troop1)
        self.reTroop2 = re.compile('%s\((\d+)\)' % troop2)


    def find_troops(self, message):
        t1 = self.reTroop1.search(message)
        if t1:
            troop1 = int(t1.group(1))
        else:
            troop1 = 0


        t2 = self.reTroop2.search(message)
        if t2:
            troop2 = int(t2.group(1))
        else:
            troop2 = 0


        return [troop1, troop2]



    def is_attackable(self, troops):
        """
        If the ratio is not exceeded then this target is safe for us to attack
        """
        if not troops[1]:
            return True

        return troops[0]/troops[1] >= settings.enemy_troop_ratio



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
    mail_parser = MailParser('Horror', 'Nightmare')

    message = ["""<b>[Hero]<\/b><br\/>ChaosLord (Lvl.15)<br\/><br\/><b>[Troops]<\/b><br\/>Horror(5351)<br>Attack(15)&nbsp;&nbsp;Defense(8)&nbsp;&nbsp;Health(80)<br><br>""",
        """<b>[Hero]<\/b><br\/>ChaosLord (Lvl.15)<br\/><br\/><b>[Troops]<\/b><br\/>Horror(5351)<br>Attack(15)&nbsp;&nbsp;Defense(8)&nbsp;&nbsp;Health(80)<br>Nightmare(1337)<br>Attack(15)&nbsp;&nbsp;Defense(8)&nbsp;&nbsp;Health(80)<br>""",
        """<b>[Hero]<\/b><br\/>ChaosLord (Lvl.15)<br\/><br\/><b>[Troops]<\/b><br\/>Nightmare(1337)<br>Attack(15)&nbsp;&nbsp;Defense(8)&nbsp;&nbsp;Health(80)<br>"""
    ]

    for m in message:
        troops = mail_parser.find_troops(m)
        print 'Troops %s' % troops

    #print 'Enemy troop ratio we are using: %d' % settings.enemy_troop_ratio
    #print 'Consider for attack: %s' % mail_parser.is_attackable(troops)


if __name__ == "__main__":
    main()
