import logging
import re

from emross import mobs

HERO_SEARCH_TEXT = 'Hero'

logger = logging.getLogger(__name__)

class MailParser:
    def __init__(self, troops=None, heroes=()):
        if not troops:
            troops = mobs.units
        self.troops = {}
        for troop in troops:
            try:
                search, count = troop
            except TypeError:
                """
                _name attr (we don't want the name alias here!) or
                the direct value of `troop`
                """
                search, count = getattr(troop, '_name', troop), 0

            self.troops[search] = {
                'count': count,
                # Support for <br>, <br/>, <br\/>
                'regex': re.compile(r'<br(?:\\?/)?>(?:{0})\((\d+)\)'.format(search))
            }

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
        """
        Search the message for the names of troops that have been configured.
        """
        troops = {}
        for troop, data in self.troops.iteritems():
            reg = data.get('regex')
            t = reg.search(message)
            if t:
                count = int(t.group(1))
                troops[troop] = count
        return troops

    def is_attackable(self, troops, troop_limits={}):
        """
        If the troop count is not exceeded for a given troop type then this target is attackable
        """
        limits = troop_limits or self.troops
        for troop, qty in troops.iteritems():
            permitted = limits.get(troop, {}).get('count', 0)
            logger.debug('Permitted: {0}'.format(permitted))

            if permitted < qty:
                return False

        return True
