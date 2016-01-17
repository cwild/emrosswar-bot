import emross
from emross.api import EmrossWar
from emross.resources import Resource
from emross.utility.task import Task


class GearForger(Task):
    INTERVAL = 3600
    URL = 'game/goods_make_api.php'

    @emross.defer.inlineCallbacks
    def forge(self, city, itemid, **kwargs):
        """
        Try to forge an Ultra item to a higher level
        TODO: This API can give non-JSON responses!
        """
        #{'code': 0, 'ret': {'cost': {'golds': 55286661604L}, 'result': 'FORGING_SUCCESS'}}
        json = yield self.bot.api.call(self.URL, action='forging', city=city.id, id=itemid, **kwargs)
        emross.defer.returnValue(json)

    @emross.defer.inlineCallbacks
    def list_items(self, **kwargs):
        """
        {
        'item_goods': [{
            'item': {
                '3027': '1',
                '3026': '1',
                '3030': '1',
                '3029': '1',
                '3028': '1'
            },
            'max_level': '40',
            's_upgrade': '6',
            's_id': '3003',
            'cost': 56953,
            'id': '12345'
        }],
        'item_material': {
            '3027': '2',
            '3026': '3',
            '3030': '2',
            '3029': '6',
            '3028': '1'
        }
        """
        json = yield self.bot.api.call(self.URL, action='forging_list', **kwargs)

        items = {}
        items['item_goods'] = json['ret'].get('item_goods', [])

        items['item_material'] = dict(json['ret'].get('item_material', {}))
        for sid, qty in items['item_material'].iteritems():
            items['item_material'][sid] = int(qty)

        emross.defer.returnValue(items)

    @emross.defer.inlineCallbacks
    def process(self, *args, **kwargs):

        continue_forging = True

        while continue_forging:
            continue_forging = False

            items = yield self.list_items()

            for forgeable in sorted(items['item_goods'], key=lambda x: int(x['s_upgrade']), reverse=True):

                if int(forgeable['s_upgrade']) >= int(forgeable['max_level']):
                    continue

                forgeable_requirements_met = True

                for required_item, qty in forgeable['item'].iteritems():
                    if int(qty) > items['item_material'].get(required_item, 0):
                        forgeable_requirements_met = False
                        break

                if not forgeable_requirements_met:
                    self.log.debug(gettext('Item requirements not met, not forgeable'))
                    continue

                city = yield self.bot.richest_city()

                requirements_met = yield city.resource_manager.meet_requirements({Resource.GOLD: int(forgeable['cost'])}, unbrick=True)
                if requirements_met:
                    json = yield self.forge(city, forgeable['id'])

                    if json['code'] == EmrossWar.SUCCESS:
                        cost = json['ret']['cost'].get('golds', forgeable['cost'])
                        city.resource_manager.modify_amount_of(Resource.GOLD, -cost)
                        city.expire()
                        continue_forging = True
