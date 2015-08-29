import gettext
gettext.install(
    'emrosswar-bot',
    'resources/locale',
    unicode=True,
    names=('gettext', 'ngettext')
)

device = 'EW-IPAD'
lang = 'en'
master = 'm.emrosswar.com'

"""
Players whom can control the bot! (applies to all bots)
"""
OPERATORS = []