import re

from emross.api import EmrossWar
from emross.utility.base import EmrossBaseObject

from lib import six


class SystemMail(EmrossBaseObject):
    DELETE_URL = 'game/dele_message_api.php'
    READ_URL = 'game/message_con_api.php'
    URL = 'game/message_api.php'

    # Which users are privileged system users? (not player generated mail)
    SYSTEM_USERS = set(['sys'])

    def delete(self, ids=[]):
        parts = map(None, *(iter(ids),) * 10)

        for part in parts:
            id_list = ','.join(str(i) for i in part)
            self.log.debug('Deleting system mail: {0}'.format(id_list))
            self.bot.api.call(self.DELETE_URL, id=id_list)

    def filter_messages(self, patterns=[], senders=set(), *args, **kwargs):

        filtered = []

        for message in self.messages():
            if senders and message['sender'] not in senders:
                self.log.debug(six.u('Skipping message due to sender mismatch: {0}').format(message))
                continue

            for pattern in patterns:
                if re.match(pattern, message['title']):
                    self.log.debug(six.u('Message title matched: pattern={0}, title={1}').format(pattern, message['title']))
                    filtered.append(message)
                    break

        return filtered

    def list(self, page=1):
        json = self.bot.api.call(self.URL, page=page)

        try:
            return json['ret']['max'], json['ret']['mail']
        except (KeyError, TypeError, ValueError):
            return 1, []

    def messages(self, page=1):
        """
        Iterate over all of the system messages
        """
        max_page = 1
        while page <= max_page:
            max_page, messages = self.list(page=page)
            for message in messages:
                yield message

            page += 1


    def read(self, mailid=None):
        if mailid is None:
            return

        return self.bot.api.call(self.READ_URL, id=mailid)

"""
http://s10.emrosswar.com/game/message_api.php?page=1

({"code":0,"ret":{"mail":[
    {"id":"1639097","sender":"sys","title":"Half Prize for Talent Reset \uff08\u5237\u65b0\u5929\u8d4b\u534a\u4ef7\u4f18\u60e0\uff09",
    "time":1392100565,"new":1},

    {"id":"1639096","sender":"sys","title":"Purchase Safety Notification\u6b3a\u8bc8\u6027\u5145\u503c\u8b66\u544a","time":1391840726,"new":1},{"id":"1639095","sender":"sys","title":"February gift package(\u4e8c\u6708\u793c\u5305\uff09","time":1391755502,"new":1},{"id":"1639094","sender":"sys","title":"Purchase Safety Notification\u6b3a\u8bc8\u6027\u5145\u503c\u8b66\u544a","time":1390958574,"new":1},{"id":"1639093","sender":"sys","title":"red envelope update(\u7ea2\u5305\u5347\u7ea7\uff09","time":1390890436,"new":1},{"id":"1639092","sender":"sys","title":"Chinese new year event \u4e2d\u56fd\u65b0\u5e74\u6d3b\u52a8","time":1390813018,"new":1},{"id":"1639091","sender":"sys","title":"Accumulative recharge bonus time correction(\u7d2f\u5145\u5956\u52b1\u65f6\u95f4\u4fee\u6b63)","time":1390810289,"new":1},{"id":"1639090","sender":"sys","title":"Chinese new year event \u4e2d\u56fd\u65b0\u5e74\u6d3b\u52a8","time":1390809631,"new":1},{"id":"1639089","sender":"sys","title":"Half Prize for Talent Reset \uff08\u5237\u65b0\u5929\u8d4b\u534a\u4ef7\u4f18\u60e0\uff09","time":1390464698,"new":1},{"id":"1639088","sender":"sys","title":"PVP ISSUE(PVP\u4e8b\u4ef6\uff09","time":1390185795,"new":1},{"id":"1639087","sender":"sys","title":"Purchase Safety Notification\u6b3a\u8bc8\u6027\u5145\u503c\u8b66\u544a","time":1390181776,"new":1},{"id":"1639086","sender":"sys","title":"Pvp issue Pvp\u95ee\u9898","time":1389954473,"new":1},{"id":"1639085","sender":"sys","title":"Weekend event(\u5468\u672b\u6d3b\u52a8\uff09","time":1389926092,"new":1},{"id":"1639084","sender":"sys","title":"The coming pvp(\u5373\u5c06\u5f00\u59cb\u7684PVP\uff09","time":1389843263,"new":1},{"id":"1639083","sender":"sys","title":"You consume, we reward(\u4f60\u6d88\u8017\uff0c\u6211\u5956\u52b1\uff09","time":1389606904,"new":1},{"id":"1639082","sender":"sys","title":"PvP issue\uff08PVP\u4e8b\u52a1\uff09","time":1389600677,"new":1},{"id":"1639081","sender":"sys","title":"PvP Start Notification","time":1389600124,"new":1},{"id":"1639080","sender":"sys","title":"Purchase Safety Notification\u6b3a\u8bc8\u6027\u5145\u503c\u8b66\u544a","time":1389577422,"new":1},{"id":"1639079","sender":"sys","title":"Huge Discount for VIP \uff08VIP\u5927\u916c\u5bbe\uff09","time":1389348036,"new":1},{"id":"1639078","sender":"sys","title":"Double hero training(\u53cc\u500d\u8bad\u7ec3\uff09","time":1389252024,"new":1}],

    "max":3}})


http://s104.emrosswar.com/game/dele_message_api.php?id=1173420%2C1173419
{"code":0,"ret":""}

http://s104.emrosswar.com/game/message_con_api.php?id=1173349
{"code":0,"ret":"he message contents"}
"""
