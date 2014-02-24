import re

HERO_SEARCH_TEXT = 'Hero'


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
            if limits.get(troop, {}).get('count', 0) < qty:
                return False
        return True
