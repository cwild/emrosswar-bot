import logging
import re

from emross.utility.base import EmrossBaseObject

import settings

logger = logging.getLogger(__name__)

class MailException: pass
class NoMailInInbox(MailException): pass

HERO_SEARCH_TEXT = 'Hero'
WAR_RESULT_INFO = 'game/war_result_info_api.php'
WAR_RESULT_LIST = 'game/war_result_list_api.php'

class Mail(EmrossBaseObject):

    def __init__(self, bot, id, data):
        super(Mail, self).__init__(bot)
        self.id = id
        self.data = data
        self.message = None
        self.processed = False

    def fetch(self):
        self.message = self.bot.api.call(WAR_RESULT_INFO, id=self.id)['ret']

    def delete(self):
        return self.bot.api.call(WAR_RESULT_LIST, action='delete', id=self.id)

    def add_fav(self, cat):
        return self.bot.favourites.add(wid=self.id, cat=cat)


class MailHandler(EmrossBaseObject):
    TYPE = None

    def __init__(self, bot):
        super(MailHandler, self).__init__(bot)
        self.mail = []

    def list_mail(self, page=1):
        json = self.bot.api.call(WAR_RESULT_LIST, page=page, type=self.TYPE)

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
            self.log.info('Deleting mail {0}'.format(ids))
            self.bot.api.call(WAR_RESULT_LIST, action='delete', id=ids)


    def process(self):
        self.mail[:] = []

        page = 1
        while True:
            _max = self.list_mail(page)
            self.log.info('Reading page {0}/{1}'.format(page, _max))

            if _max == page:
                break
            page += 1


class AttackMailHandler(MailHandler):
    TYPE = -1

    def process(self):
        self.log.info('Cleaning up war reports...')
        super(AttackMailHandler, self).process()

        # Now delete the mails
        processed_mail = [m for m in self.mail if m.data['dname'] is None]

        self.delete_bulk(processed_mail)
        self.mail[:] = []

class ScoutMailHandler(MailHandler):
    TYPE = 3

    def __init__(self, bot):
        super(ScoutMailHandler, self).__init__(bot)
        self.parser = MailParser(settings.enemy_troops)

    def process(self):
        """
        Read through all scout reports and examine the reports
        we have of any devil armies
        """
        super(ScoutMailHandler, self).process()

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


                self.log.info('%s devil army at [%d/%d] with troops %s' % (result, mail.data['dx'], mail.data['dy'],
                    ', '.join(['%s(%d)'] * len(settings.enemy_troops)) % sum(zip([s for s, c in settings.enemy_troops], troops), ())))


                mail.processed = True
            except TypeError:
                self.log.warning('Error parsing mail: %s\n\n%s\n\n\n%s' % (mail.data, mail.message, '*'*40))



        # Now delete the mails
        processed_mail = [m for m in self.mail if m.processed]

        self.delete_bulk(processed_mail)

        self.mail[:] = [m for m in self.mail if not m.processed]


class MailParser:
    def __init__(self, troops=(), heroes=()):
        self.troops = {}
        for troop, count in troops:
            self.troops[troop] = {'count': count, 'regex': re.compile('{0}\((\d+)\)'.format(troop))}

        self.reHeroes = []
        for hero in heroes:
            obj = hero, re.compile(r'<b>\[{0}\]<\\/b><br\\/>({1})'.format(HERO_SEARCH_TEXT, hero))
            self.reHeroes.append(obj)


    def find_hero(self, message):
        for hero, reg in self.reHeroes:
            t = reg.search(message)
            if t:
                return t.group(1)

    def find_troops(self, message):
        troops = {}
        for troop, data in self.troops.iteritems():
            reg = data.get('regex')

            t = reg.search(message)
            if t:
                count = int(t.group(1))
                troops[troop] = count

        return troops


    def is_attackable(self, troops):
        """
        If the troop count is not exceeded for a given troop type then this target is attackable
        """

        for troop, qty in troops.iteritems():

            if self.troops.get(troop, {}).get('count', 0) < qty:
                return False

        return True
