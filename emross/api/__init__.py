from emross.api.core import EmrossWarApi, EmrossWar

def config_fix(original):

    s = original[original.find('{') : original.rfind('}')+1]
    s = s.replace(':!0', ':1').replace(':!1', ':0')

    try:
        import sys
        sys.path.append('lib/demjson')

        import demjson
        _json = demjson.decode(s)
    except Exception:
        import re
        import json

        s = re.sub("""([A-Z_0-9]+):""", '"\g<1>":', s)
        _json = json.loads(s)

    return _json

EmrossWar.extend('CONFIG', 'data/config.js', decoder=config_fix)

# Cleanup
del config_fix

EmrossWar.extend('LANG', 'translation/%(lang)s/lng.js')
EmrossWar.extend('TRANSLATE', 'translation/%(lang)s/translate.js')
