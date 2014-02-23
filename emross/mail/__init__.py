SYSTEM_MAIL = 'game/message_api.php'
WAR_RESULT_INFO = 'game/war_result_info_api.php'
WAR_RESULT_LIST = 'game/war_result_list_api.php'

from emross.mail.handlers import AttackMailHandler, ScoutMailHandler
from emross.mail.message import Mail
from emross.mail.parser import MailParser


class MailException:
    pass

class NoMailInInbox(MailException):
    pass
