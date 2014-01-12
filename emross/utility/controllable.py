from emross.api import EmrossWar
from emross.chat import Chat
from emross.utility.base import EmrossBaseObject

class Controllable(EmrossBaseObject):
    COMMAND = None
    SUB_COMMAND_OVERRIDES = {}

    def __init__(self, *args, **kwargs):
        super(Controllable, self).__init__(*args, **kwargs)

        self.chat = self.bot.builder.task(Chat)

        if self.COMMAND:
            self.bot.events.subscribe(self.COMMAND, self._controller)

    def _controller(self, action=None, *args, **kwargs):
        try:
            # Allow commands to be aliased/renamed
            action = self.SUB_COMMAND_OVERRIDES.get(action) or action

            method = getattr(self, 'action_{0}'.format(action), self.action_help)
            method(*args, **kwargs)
        except Exception as e:
            self.log.exception(e)

    def help(self, *args, **kwargs):
        self.chat.send_message("I do not understand what you want me to do.")

    def action_help(self, for_method=None, *args, **kwargs):
        """
        Provide basic usage info on the specified command.
        """

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
