from emross.api import EmrossWar
from emross.api.cache import EmrossDataHandler

class ScenarioDataHandler(EmrossDataHandler):
    def map_name(self, scenario=0):
        return self.data['campaign']['INFO']['campaign_{0}_mapname'.format(scenario)]

    def point_name(self, scenario=0, point=1):
        try:
            return self.data['campaign']['INFO']['campaign_{0}_npclist_{1}_pointname'.format(scenario, point)]
        except KeyError:
            return 'UNKNOWN point ({0})'.format(point)

EmrossWar.extend('SCENARIO_TEXT', 'translation/%(lang)s/campaign.lng.js', model=ScenarioDataHandler)
