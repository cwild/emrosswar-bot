device = 'EW-IPAD'
lang = 'en'

from emross.api.core import EmrossWarApi, EmrossWar

EmrossWar.extend('LANG', 'translation/%(lang)s/lng.js')
