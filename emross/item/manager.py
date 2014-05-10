import re

from lib.cacheable import CacheableData

from emross.api import EmrossWar
from emross.item import item
from emross.utility.controllable import Controllable


class InventoryManager(Controllable, CacheableData):
    CACHE_LIFETIME = 1800
    COMMAND = 'inventory'
    ITEM_PAGES = (
        item.ItemType.WEAPON,
        item.ItemType.ARMOR,
        item.ItemType.MOUNT,
        item.ItemType.RING,
        item.ItemType.BOOK,
        item.ItemType.ITEM,
    )

    def __init__(self, bot):
        super(InventoryManager, self).__init__(bot, time_to_live=self.CACHE_LIFETIME)

    def update(self, *args, **kwargs):
        data = {}
        known_ids = set()

        for item_type in self.ITEM_PAGES:
            page = 1
            while True:
                json = self.bot.item_manager.list(page=page, type=item_type)

                for _item in json['ret']['item']:
                    try:
                        known_ids.add(_item['item']['id'])

                        sid = data.setdefault(_item['item']['sid'], {})
                        sid.update({_item['item']['id']: _item})
                    except Exception as e:
                        self.log.exception(e)

                page += 1
                if page > json['ret']['max']:
                    self.log.debug('Last page of item type {0}'.format(item_type))
                    break


        # Clean-up any obsolete items
        for sid, ids in data.iteritems():
            data[sid] = dict((k, v) for k, v in ids.iteritems() if k in known_ids)

        return dict((k,v) for k, v in data.iteritems() if v)


    def adjust_item_stock(self, item_id, qty=1):
        try:
            for sid, values in self._data.iteritems():
                values[int(item_id)]['item']['num'] += qty

                if values[int(item_id)]['item']['num'] < 1:
                    del values[int(item_id)]

                return
        except KeyError:
            pass

    def action_search(self, event, *args, **kwargs):
        """
        Locate items from the inventory
        """
        search_items = []
        for _search in args:
            for _id, _item in EmrossWar.ITEM.iteritems():
                try:
                    if re.search(_search, _item.get('name'), re.IGNORECASE):
                        search_items.append(int(_id))
                except re.error:
                    pass

        found = self.bot.find_inventory_items(search_items)
        result = []
        for item_id, values in found.iteritems():
            name = EmrossWar.ITEM[str(item_id)].get('name')
            vals = [qty for uniqid, qty, sellable in values]
            result.append(u'{0}={1}'.format(name, sum(vals)))

        if result:
            self.chat.send_message(
                u'Cache: {0}'.format(', '.join(result)), event=event
            )
        else:
            self.chat.send_message('Sorry, I do not have any of those items!')
