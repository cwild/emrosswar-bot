from emross.api.core import EmrossWarApi, EmrossWar

EmrossWar.extend('LANG', 'translation/%(lang)s/lng.js')
EmrossWar.extend('TRANSLATE', 'translation/%(lang)s/translate.js')
