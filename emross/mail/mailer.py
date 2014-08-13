from emross.api import EmrossWar
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


    def send_mail(self, recipient, title, message, category=CATEGORY, **kwargs):
        """
        Actually handle the sending of mail. We might need to send the message
        in chunks
        """

        if recipient == self.bot.userinfo['nick']:
            return

        if not message:
            raise ValueError('No message body provided, unable to send mail')

        return self.bot.api.call(self.URL,
            nick=recipient.encode('utf-8'),
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
