import platform
import subprocess

from emross.utility.controllable import Controllable


class AboutHelper(Controllable):
    COMMAND = 'about'

    def action_platform(self, event, method='platform', *args, **kwargs):
        """
        Information about the platform I am running on.
        """
        func = getattr(platform, method, 'platform')
        self.chat.send_message('Platform: "{0}"'.format(func(**kwargs)))

    def action_version(self, event, *args, **kwargs):
        """
        Current branch hash
        """
        command = ['git', 'rev-parse', 'HEAD']
        try:
            git_hash = subprocess.check_output(command)
        except AttributeError:
            git_hash = subprocess.Popen(command, stdout=subprocess.PIPE).communicate()[0]

        self.chat.send_message('commit: {0}'.format(git_hash))
