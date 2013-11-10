import time

from lib.cacheable import CacheableData

from emross.favourites import FAVOURITES_URL
from emross.utility.base import EmrossBaseObject

REPORT_LIFETIME = 3600
REPORT_MAX_AGE = 86400

class NPC(EmrossBaseObject):
    def __init__(self, data, bot):
        super(NPC, self).__init__(bot)
        #[[14785,115,248,1,3]
        # Seems that x,y are back to front
        self._data = data
        self.id = data[0]
        self.x = data[2]
        self.y = data[1]
        self.rating = data[3]
        self.attack = data[4]
        self._setup_report()

    def _setup_report(self):
        """
        api_fav.php
        act=getfavnpc fid=113732
        {"code":0,"ret":{"fav":[1352423302,"<b>[Hero]<\/b><br\/>ChaosLord (Lvl.15)<br\/><br\/><b>[Troops]<\/b><br\/>Horror(4923)<br>Attack(15)&nbsp;&nbsp;Defense(8)&nbsp;&nbsp;Health(80)<br><br>Nightmare(452)<br>Attack(60)&nbsp;&nbsp;Defense(10)&nbsp;&nbsp;Health(100)<br><br>"]}}
        """
        def _fetch_report(*args, **kwargs):
            try:
                report = self.bot.session.mobs[self.id]
                if time.time() < report.get('timestamp',0) + REPORT_MAX_AGE:
                    return report
            except (AttributeError, KeyError):
                self.bot.session.mobs = {}

            json = self.bot.api.call(*args, **kwargs)
            timestamp, msg = json['ret'].get('fav', (0, ''))

            result = {
                'timestamp': timestamp,
                'hero': self.bot.scout_mail.parser.find_hero(msg),
                'troops': self.bot.scout_mail.parser.find_troops(msg),
            }

            self.bot.session.mobs[self.id] = result
            return result

        self._report = CacheableData(time_to_live=REPORT_LIFETIME,
                        update=_fetch_report, method=FAVOURITES_URL,
                        act='getfavnpc', fid=self.id)

    @property
    def report(self):
        return self._report.data
