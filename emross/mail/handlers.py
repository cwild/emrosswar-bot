import time

from emross.api import EmrossWar
from emross.mail import MailException, NoMailInInbox, WAR_RESULT_LIST
from emross.mail.message import Mail
from emross.mail.parser import MailParser
from emross.utility.base import EmrossBaseObject

import settings

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
            self.log.debug('Deleting mail {0}'.format(ids))
            self.bot.api.call(WAR_RESULT_LIST, action='delete', id=ids)

    def process(self):
        self.mail[:] = []

        page = 1
        while True:
            _max = self.list_mail(page)
            self.log.debug('Reading page {0}/{1}'.format(page, _max))

            if _max == page:
                break
            page += 1


class AttackMailHandler(MailHandler):
    TYPE = -1
    CLEANUP_WAIT = 300

    def process(self, war_report_cleanup_delay=CLEANUP_WAIT, delete_losses=False, **kwargs):
        self.log.info('Cleaning up war reports')
        super(AttackMailHandler, self).process()

        # Now delete the mails
        processed_mail = []
        for m in self.mail:
            if m.data['dname'] is not None:
                continue

            if war_report_cleanup_delay is False:
                self.log.debug('Do not delete any war reports')
                continue
            else:
                interval = time.time() - m.data.get('time', 0)
                if interval < war_report_cleanup_delay:
                    self.log.debug('Leave war report {0} for at least a further {1}'.format(\
                        m.data['id'], interval-war_report_cleanup_delay))
                    continue

            if not delete_losses:
                if self.bot.userinfo['id'] == m.data['aid'] and m.data['flag'] != 1:
                    self.log.debug('War report id={0} did not win. Do not delete.'.format(m.id))
                    continue

            processed_mail.append(m)


        self.delete_bulk(processed_mail)
        self.mail[:] = []


class ScoutMailHandler(MailHandler):
    TYPE = 3

    def __init__(self, bot):
        super(ScoutMailHandler, self).__init__(bot)
        self.parser = MailParser(settings.enemy_troops)

    def process(self, add_scout_report_func=None, **kwargs):
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

                if not add_scout_report_func:
                    continue

                mail.fetch()

                troops = self.parser.find_troops(mail.message['scout_report']['result'])
                if add_scout_report_func(troops):
                    result = 'ADDED'
                    mail.add_fav(2)
                else:
                    result = 'REJECTED'

                vals = []
                for name, qty in troops.iteritems():
                    vals.append('{0}({1})'.format(name, qty))
                vals = ', '.join(vals)

                self.log.info('{0} {npc} at [{1}/{2}] with troops {3}'.format(\
                    result, mail.data['dx'], mail.data['dy'], vals,
                    npc=EmrossWar.LANG.get('MONSTER', 'DevilArmy'))
                )

                mail.processed = True
            except TypeError:
                self.log.warning('Error parsing mail: %s\n\n%s\n\n\n%s' % (mail.data, mail.message, '*'*40))


        # Now delete the mails
        processed_mail = [m for m in self.mail if m.processed]
        self.delete_bulk(processed_mail)

        self.mail[:] = [m for m in self.mail if not m.processed]
