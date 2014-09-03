from emross.api import EmrossWar
from emross.utility.controllable import Controllable
from emross.utility.task import Task

from lib import six


class MailMan(Task, Controllable):
    COMMAND = 'mailman'

    def setup(self):
        try:
            self._mailman = self.bot.session.mailman
        except AttributeError:
            self._mailman = self.bot.session.mailman = {}

    @property
    def groups(self):
        return self._mailman.setdefault('groups', {})

    def action_groups(self, event, *args, **kwargs):
        """
        List the current groups
        """
        if not self.groups:
            self.chat.send_message(six.u('No groups have been created!'), event=event)
            return

        self.chat.send_message(six.u('Current usergroups: {0}').format(
            six.u(', ').join(self.groups.iterkeys())
        ), event=event)

    def action_adduser(self, event, user, group, *args, **kwargs):
        """
        Add a user to a group
        """
        self.groups.setdefault(group, set()).add(user)

    def action_deluser(self, event, user, group, *args, **kwargs):
        """
        Remove a user from a group
        """
        try:
            self.groups[group].remove(user)

            # Clear empty groups
            if not self.groups[group]:
                del self.groups[group]
        except KeyError:
            pass

    def action_show(self, event, group, *args, **kwargs):
        """
        List all the groups that the user is a member of
        """
        members = self.groups.get(group)
        if not members:
            self.chat.send_message(six.u('Group "{0}" not found').format(group),
                event=event
            )
            return

        self.chat.send_message(six.u('Members in group "{0}": {1}').format(group,
            six.u(', ').join(members)
        ), event=event)

    def action_usergroups(self, event, user, *args, **kwargs):
        """
        List all the groups that the user is a member of
        """
        groups = []
        for group, members in self.groups.iteritems():
            if user in members:
                groups.append(group)

        self.chat.send_message(six.u('{0} is a member of: {1}').format(user,
            six.u(', ').join(groups)
        ), event=event)
