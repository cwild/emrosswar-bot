import functools
import logging

from emross.utility.base import EmrossBaseObject

logger = logging.getLogger(__name__)


def subscriber(method=None, **outer):
    """
    If called without method, we've been called with optional arguments.
    We return a decorator with the optional arguments filled in.
    Next time round we'll be decorating method.
    """
    if method is None:
        return functools.partial(subscriber, **outer)

    @functools.wraps(method)
    def wrapped(*args, **kwargs):
        outer.update(kwargs)
        return method(*args, **outer)

    return wrapped


class EventManager(EmrossBaseObject):
    """
    Provide an interface for the bot to react to events in a pre-determined way.
    """

    def __init__(self, bot):
        super(EventManager, self).__init__(bot)
        self.events = {}

    def subscribe(self, event, action):
        self.events.setdefault(event, []).append(action)

    def notify(self, event, *args, **kwargs):
        """
        Raise the given "event" with all of its subscribers
        """

        for action in self.events.get(event, []):
            try:
                action(*args, **kwargs)
            except Exception as e:
                logger.exception(e)

    def unsubscribe(self, event, action):
        try:
            self.events[event].remove(action)
        except (KeyError, ValueError):
            pass
