import random
import Queue

from emross.api import EmrossWar
from emross.chat import Chat
from emross.utility.task import Task

class Control(Task):
    INTERVAL = 1
    PVP_COMMAND = 'pvp'

    def setup(self):
        self.bot.events.subscribe(self.PVP_COMMAND, self._controller)
        self.chat = self.bot.builder.task(Chat)
        self.queue = Queue.Queue()

    def _controller(self, action=None, *args, **kwargs):
        try:
            method = getattr(self, 'action_{0}'.format(action), self.action_help)
            method(*args, **kwargs)
        except Exception as e:
            self.log.exception(e)

    def help(self, *args, **kwargs):
        self.chat.send_message("I do not understand what you want me to do.")

    def action_help(self, for_method=None, *args, **kwargs):
        method = getattr(self, 'action_{0}'.format(for_method))
        if method and method.__doc__:
            self.chat.send_message(method.__doc__.strip())

    def action_enter(self, *args, **kwargs):
        """I will attempt to join the PvP world in the next {delay|30} seconds."""
        delay = int(kwargs.get('delay', 30))
        self.sleep(random.randint(1, delay))

        def pvp_check(user, **_kwargs):
            from emross import master as MASTER
            json = self.bot.api.call('info.php', server=MASTER, user=user, action='getpvpserver')

            if json['code'] == EmrossWar.SUCCESS:
                server = json['ret']['server'][7:-1]
                json = self.bot.api.call(self.bot.api.player.LOGIN_URL, \
                    server=server, user=user, action='synckey')

                json = self.bot.api.call(self.bot.USERINFO_URL, server=server)

                self.chat.send_message('PvP world: {0}, player "{1}" at ({x},{y})'.format(\
                    server, json['ret']['user']['nick'],
                    x=json['ret']['user']['city']['x'],
                    y=json['ret']['user']['city']['y']))

        self.queue.put((pvp_check, (self.bot.api.player.username,), {}))

    def process(self, *args, **kwargs):
        """
        Look to perform PvP tasks automatically.
        """

        try:
            job = self.queue.get_nowait()
            method, _args, _kwargs = job
            method(*_args, **_kwargs)
        except Queue.Empty:
            pass
