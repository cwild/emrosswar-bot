from emross.api import EmrossWar
from emross.mail.mailman import MailMan
from emross.utility.controllable import Controllable


class Mailer(Controllable):
    COMMAND = 'mail'
    CATEGORY = 0
    URL = 'game/inter_message_api.php'

    def action_send(self, event, *args, **kwargs):
        """
        Send a mailing to another player
        """
        self.send_mail(*args, **kwargs)


    def send_mail(self, title, message, recipient=None, group=None, category=CATEGORY, **kwargs):
        """
        Actually handle the sending of mail. We might need to send the message
        in chunks
        """

        if not message:
            raise ValueError('No message body provided, unable to send mail')

        if group:
            usergroup = self.bot.builder.task(MailMan).groups.get(group, set())
        else:
            usergroup = set([recipient])

        for user in usergroup:
            if user == self.bot.userinfo['nick']:
                continue

            self.bot.api.call(self.URL,
                nick=user.encode('utf-8'),
                title=title.encode('utf-8'),
                body=message.encode('utf-8'), category=category, **kwargs)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    from bot import bot
    mailer = Mailer(bot)

    message = []
    for l in [chr(i) for i in xrange(65, 65+62)]:
        message.append(l*10)

    message = '\n'.join(message)

    mailer.send_mail(None, 'You have mail!', message)
