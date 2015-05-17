import copy
import re
import sys

from lib.cacheable import CacheableData
from lib import six

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
        for sid, values in self._data.iteritems():
            try:
                values[int(item_id)]['item']['num'] += qty

                if values[int(item_id)]['item']['num'] < 1:
                    del values[int(item_id)]

                return
            except KeyError:
                pass

    def _get_all_items(self):
        """
        Load the cached client item dict but update with other items from
        our inventory where necessary
        """
        all_items = copy.deepcopy(EmrossWar.ITEM.data)

        for _type in self.data.itervalues():
            for _data in _type.itervalues():
                _item = _data['item']
                new_data = {
                    'name': _item.get('name'),
                    'desc': _item.get('desc'),
                    'img': _item.get('img'),
                    'sid': str(_item.get('sid')),
                }
                all_items.setdefault(new_data['sid'], {}).update(new_data)
        return all_items

    def find_search_items_from_names(self, *args):
        all_items = self._get_all_items()

        search_items = []
        for _search in args:
            for _id, _item in all_items.iteritems():
                try:
                    if re.search(_search, _item.get('name'), re.IGNORECASE):
                        search_items.append(int(_id))
                except re.error:
                    pass

        return search_items

    def action_data(self, event, *args, **kwargs):
        """
        Find data about a specific item
        """
        for _search in args:
            for _id, _item in self._get_all_items().iteritems():
                try:
                    if re.search(_search, _item.get('name'), re.IGNORECASE):
                        self.chat.send_message(
                            _('Found {0}: {1}').format(_search, _item),
                            event=event
                        )
                except re.error:
                    pass

    def action_search(self, event, *args, **kwargs):
        """
        Locate items from the inventory
        """
        all_items = self._get_all_items()
        search_items = self.find_search_items_from_names(*args)

        found = self.bot.find_inventory_items(search_items)
        result = []
        for item_id, values in found.iteritems():
            name = all_items[str(item_id)].get('name')
            vals = [qty for uniqid, qty, sellable in values]
            result.append(six.u('{0}={1}').format(name, sum(vals)))

        if result:
            self.chat.send_message(
                six.u('Cache: {0}').format(', '.join(result)), event=event
            )
        elif 'quiet' not in kwargs:
            self.chat.send_message('Sorry, I do not have any of those items!')

    def action_use(self, event, *args, **kwargs):
        """Use a given item, eg. sid=123"""

        sid = kwargs.get('sid')
        if sid:
            sid = int(sid)

        found = self.data.get(sid)

        if not found:
            if 'quiet' not in kwargs:
                self.chat.send_message(_('I do not have any of those!'),
                    event=event)

            return

        item_manager = self.bot.item_manager

        try:
            num = kwargs.get('num', 1)
            if num == '*':
                num = sys.maxsize
            else:
                num = int(num)
        except ValueError:
            num = 0

        total, work = 0, True
        while work and total < num:
            used = 0

            for item_id, item in found.iteritems():
                if not work:
                    break
                if not item['use']:
                    self.log.debug(_('Unable to use item: {0}').format(item))
                    continue

                times = min(item['item']['num'], num) - total
                for c in six.moves.range(times):
                   json = item_manager.use(self.bot.cities[0], item_id)

                   if json['code'] == EmrossWar.SUCCESS:
                       used += 1

                       feedback = []
                       feedback.append((json['ret'].get('ep'), EmrossWar.LANG['EMRONOR']))
                       feedback.append((json['ret'].get('gem'), EmrossWar.LANG['MONEY']))

                       for _item in json['ret'].get('item', []):
                           feedback.append((_item['num'],
                               _item.get('name') or
                               EmrossWar.ITEM.data.get(str(_item['sid']), {}).get('name') or
                               'sid:{0}'.format(_item['sid'])
                           ))

                       msg = ['{0}*{1}'.format(qty, name) for qty, name in feedback if qty]
                       if msg:
                           self.chat.send_message(', '.join(msg), event=event)
                   else:
                       # Something wrong, stop using items
                       work = False
                       break

            total += used
            if not used:
                break
