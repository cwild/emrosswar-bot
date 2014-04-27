import functools

from emross.api import EmrossWar
from emross.chat import Chat
from emross.utility.base import EmrossBaseObject


class Controllable(EmrossBaseObject):
    COMMAND = None
    COMMAND_PASSWORD = None
    SUB_COMMAND_OVERRIDES = {}

    def __init__(self, *args, **kwargs):
        super(Controllable, self).__init__(*args, **kwargs)

        self.chat = self.bot.builder.task(Chat)

        if self.COMMAND:
            self.bot.events.subscribe(self.COMMAND, self._controller)

    def _controller(self, event, action=None, *args, **kwargs):
        try:
            # Allow commands to be aliased/renamed
            action = self.SUB_COMMAND_OVERRIDES.get(action) or action

            method = getattr(self, 'action_{0}'.format(action), self.action_help)
            method(event, *args, **kwargs)
        except Exception as e:
            self.log.exception(e)

    def help(self, *args, **kwargs):
        self.chat.send_message("I do not understand what you want me to do.")

    def action_help(self, event, for_method=None, *args, **kwargs):
        """
        Provide basic usage info on the specified command.
        """
        event.propagate = False

        # Help should reflect our aliased commands as well
        for_method = self.SUB_COMMAND_OVERRIDES.get(for_method) or for_method
        method = getattr(self, 'action_{0}'.format(for_method), None)

        message = None

        if method:
            if method.__doc__:
                message = method.__doc__.strip()
            else:
                message = 'I have no idea about "{0}"!'.format(for_method)
        else:
            message = 'Choose from the following: {0}'.format(','.join([
                    attrib.replace('action_', '') for attrib in dir(self)
                    if attrib.startswith('action_')
                ]))

        if message:
            self.chat.send_message(message, **kwargs)

    @classmethod
    def restricted(cls, method=None, password=True, **outer):
        """
        If called without method, we've been called with optional arguments.
        We return a decorator with the optional arguments filled in.
        Next time round we'll be decorating method.
        """
        if method is None:
            return functools.partial(cls.restricted, password=password, **outer)

        @functools.wraps(method)
        def wrapped(self, *args, **kwargs):

            if password:
                if not self.COMMAND_PASSWORD:
                    self.log.debug('This command requires a password.')
                    return

                if self.COMMAND_PASSWORD.lower() != kwargs.get('password', '').lower():
                    self.log.debug('The command password does not match!')
                    return

            outer.update(kwargs)
            return method(self, *args, **outer)

        return wrapped
