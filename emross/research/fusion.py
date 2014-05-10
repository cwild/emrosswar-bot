from emross.api import EmrossWar
from emross.item.item import ItemRank, ITEMS
from emross.resources import Resource
from emross.utility.controllable import Controllable
from emross.utility.task import Task

RARE_ITEM_TIERS = {}

for sid, item in ITEMS.iteritems():
    if item['rank'] >= ItemRank.RARE:
        RARE_ITEM_TIERS.setdefault(item['type'], []).append(sid)


for vals in RARE_ITEM_TIERS.itervalues():
    # Ascending, better items defined first (generally!)
    vals.sort(reverse=True)

# Clean up
del sid, item, vals


class AutoFusion(Task, Controllable):
    DOWNGRADE_FUSEABLE = False
    FUSION_COST = 1500000
    INTERVAL = 3600
    COMBINE_URL = 'game/goods_combine.php'
    REPORT = True

    def find_fuseable_combos(self, items, tier, fuse_below, downgrade):
        combos = {}

        for item_id, sid, enhance in items:
            _type = int(EmrossWar.ITEM[str(sid)]['type'])

            if RARE_ITEM_TIERS[_type].index(sid)+1 < tier:
                # We might not always want to fuse an upgraded item
                if downgrade or enhance < fuse_below:
                    combos.setdefault(sid, []).append((item_id, enhance))


        combos = dict([(sid, sorted(ids, key=lambda i:i[1])[:3])
                    for sid, ids in combos.iteritems() if len(ids) >= 3])

        if combos:
            self.log.info('Fuseable items: {0}'.format(','.join(
                ['"{0}" ({1})'.format(EmrossWar.ITEM[str(sid)]['name'], vals)
                for sid, vals in combos.iteritems()
                ]
            )))

        return combos

    def fuse_items(self, city, *items):
        """
        Combine 3 items to upgrade one of the them to the next item tier
        Pass items as (item_id, enhance)
        """

        kwargs = {}
        for i, item in enumerate(items, start=1):
            item_id, enhance = item
            kwargs['item{0}'.format(i)] = item_id

            for _ in range(enhance):
                json = self.bot.item_manager.downgrade(city, item_id)
                if json['code'] != EmrossWar.SUCCESS:
                    break

        return self.bot.api.call(self.COMBINE_URL, action='combine',
                            city=city.id, **kwargs)

    def list_items(self):
        self.log.info('List items available for fusion')

        items = []
        json = self.bot.api.call(self.COMBINE_URL, action='list')

        if json['code'] == EmrossWar.SUCCESS:
            for _item in json['ret']['items']:
                item_id, sid, enhance = map(int, _item)
                items.append((item_id, sid, enhance))

        return items

    def process(self, tier=2, fuse_below=1, report=REPORT, downgrade=DOWNGRADE_FUSEABLE, **kwargs):

        # Keep fusing items until there are no more left or the required gold is not met
        finished = False

        while not finished:
            items = self.list_items()
            fuseable = self.find_fuseable_combos(items, tier, fuse_below, downgrade)

            if not fuseable:
                self.log.info('Nothing to fuse')
                break

            for fuseitems in fuseable.itervalues():
                city = self.bot.richest_city()
                if city.resource_manager.meet_requirements({Resource.GOLD: self.FUSION_COST}, **kwargs):
                    json = self.fuse_items(city, *fuseitems)

                    if json['code'] == EmrossWar.SUCCESS:
                        msg = 'Successfully fused: "{0}"'.format(json['ret']['name'])
                        self.log.info(msg)
                        city.expire()

                        if report:
                            self.chat.send_message(msg)
                else:
                    finished = True
                    break


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    for item_type in range(1,7):
        logging.info('type {0}\n{1}'.format(item_type, '*'*40))
        for sid in RARE_ITEM_TIERS[item_type]:
            logging.info(EmrossWar.ITEM[str(sid)].get('name'))
