import random
from lib.six.moves import queue


from emross.api import EmrossWar
from emross.utility.controllable import Controllable
from emross.utility.task import Task

class Control(Task, Controllable):
    INTERVAL = 1
    COMMAND = 'pvp'

    def setup(self):
        self.queue = queue.Queue()

    def action_enter(self, event, *args, **kwargs):
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
                    server, EmrossWar.safe_text(json['ret']['user']['nick']),
                    x=json['ret']['user']['city'][0]['x'],
                    y=json['ret']['user']['city'][0]['y']))

        self.queue.put((pvp_check, (self.bot.api.player.username,), {}))

    def process(self, *args, **kwargs):
        """
        Look to perform PvP tasks automatically.
        """

        try:
            job = self.queue.get_nowait()
            method, _args, _kwargs = job
            method(*_args, **_kwargs)
        except queue.Empty:
            pass
