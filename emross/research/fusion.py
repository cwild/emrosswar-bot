from emross.api import EmrossWar
from emross.item.item import ItemRank, ITEMS
from emross.resources import Resource
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


class AutoFusion(Task):
    FUSION_COST = 1500000
    INTERVAL = 3600
    COMBINE_URL = 'game/goods_combine.php'

    def find_fuseable_combos(self, items, tier):
        combos = {}
        for item_id, sid, enhance in items:
            _type = int(EmrossWar.ITEM[str(sid)]['type'])
            if RARE_ITEM_TIERS[_type].index(sid)+1 < tier:
                combos.setdefault(sid, []).append(item_id)

        combos = dict([(sid, ids[:3]) for sid, ids in combos.iteritems() if len(ids) >= 3])
        for sid, vals in combos.iteritems():
            self.log.info('Fuseable items: "{0}", {1}'.format(\
                EmrossWar.ITEM[str(sid)]['name'], vals))

        return combos.values()

    def fuse_items(self, city, item1, item2, item3):
        """
        Combine 3 items to upgrade one of the them to the next item tier
        """
        json = self.bot.api.call(self.COMBINE_URL, action='combine',
                            city=city.id, item1=item1, item2=item2, item3=item3)

        if json['code'] == EmrossWar.SUCCESS:
            self.log.info('Successfully fused: "{0}"'.format(json['ret']['name']))
            return True

        return False

    def list_items(self, fuse_below=1):
        self.log.info('List items available for fusion')

        items = []
        json = self.bot.api.call(self.COMBINE_URL, action='list')

        if json['code'] == EmrossWar.SUCCESS:
            for _item in json['ret']['items']:
                item_id, sid, enhance = map(int, _item)

                if enhance < fuse_below:
                    i = (item_id, sid, enhance)
                    items.append(i)

        return items

    def process(self, tier=2, fuse_below=1, **kwargs):

        # Keep fusing items until there are no more left or the required gold is not met
        finished = False

        while not finished:
            items = self.list_items(fuse_below)
            fuseable = self.find_fuseable_combos(items, tier)

            if not fuseable:
                self.log.info('Nothing to fuse')
                break

            for item1, item2, item3 in fuseable:
                city = self.bot.richest_city()
                if city.resource_manager.meet_requirements({Resource.GOLD: self.FUSION_COST}, **kwargs):
                    if self.fuse_items(city, item1, item2, item3):
                        city.expire()
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
