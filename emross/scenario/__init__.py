from emross.api import EmrossWar
from emross.api.cache import EmrossDataHandler

class ScenarioDataHandler(EmrossDataHandler):
    def map_name(self, scenario=0):
        return self.data['campaign']['INFO']['campaign_%d_mapname' % scenario]

    def point_name(self, scenario=0, point=1):
        try:
            return self.data['campaign']['INFO']['campaign_%d_npclist_%d_pointname' % (scenario, point)]
        except KeyError:
            return 'UNKNOWN point (%d)' % point

EmrossWar.extend('SCENARIO_TEXT', 'translation/%(lang)s/campaign.lng.js', model=ScenarioDataHandler)
