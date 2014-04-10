import functools

from emross.utility.base import EmrossBaseObject

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


class Event(object):
    """
    Store information about an event.
    """
    def __init__(self, name, **kwargs):
        self.name = name
        self.data = kwargs
        self.propagate = True

    def __getattr__(self, name):
        return self.data.get(name)

class EventManager(EmrossBaseObject):
    """
    Provide an interface for the bot to react to events in a pre-determined way.
    """

    def __init__(self, bot):
        super(EventManager, self).__init__(bot)
        self.events = {}

    def subscribe(self, event_name, action):
        self.events.setdefault(event_name, []).append(action)

    def notify(self, event, *args, **kwargs):
        """
        Raise the given "event" with all of its subscribers
        """
        self.log.debug('Process event "{0}" with {1} and {2} (meta-data={meta})'.format(\
            event.name, args, kwargs, meta=event.data))

        for action in self.events.get(event.name, []):
            if not event.propagate:
                self.log.debug('Do not further propagate "{0}"'.format(event.name))
                break

            try:
                action(event, *args, **kwargs)
            except Exception as e:
                self.log.exception(e)

    def unsubscribe(self, event_name, action):
        try:
            self.events[event_name].remove(action)
        except (KeyError, ValueError):
            pass
