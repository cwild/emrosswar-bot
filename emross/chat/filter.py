from emross.utility.base import EmrossBaseObject
from emross.utility.parser import SkipMessage


class PlayerFilter(EmrossBaseObject):
    def filter(self, *args, **kwargs):
        try:
            for kwarg, value in kwargs.iteritems():
                filter = getattr(self, 'filter_{0}'.format(kwarg))
                filter(value)
        except SkipMessage:
            raise
        except Exception:
            pass

    def filter_level(self, level):
        current_lvl = int(self.bot.userinfo.get('level', 0))
        exact_lvl, min_lvl, max_lvl = None, 0, 999
        try:
            if '-' in level:
                parts = map(int, level.split('-', 1))
                min_lvl = parts.pop(0)
                max_lvl = parts.pop(0)
            else:
                exact_lvl = int(level) == current_lvl
        except (IndexError, ValueError):
            pass

        if exact_lvl is not None:
            if not exact_lvl:
                raise SkipMessage('Does not match exact level. Current={0}, specified={1}'.format(current_lvl, level))

        elif not min_lvl <= current_lvl <= max_lvl:
            raise SkipMessage('Not within specified level range, stop processing')

    # Alias for level/levels usage (I usually forget which it is!)
    filter_levels = filter_level
