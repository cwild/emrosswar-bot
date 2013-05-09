import logging

from emross.api import EmrossWar
from emross.item import inventory
from emross.quests import Quest, QuestManager
from emross.utility.task import Task

logger = logging.getLogger(__name__)

class ChestOpener(Task):
    QUESTS = set([Quest.BRONZE_KEY, Quest.SILVER_KEY])

    def __init__(self, bot):
        super(ChestOpener, self).__init__(bot, __name__)

    def setup(self):
        self.quest_manager = QuestManager(self.bot)

    def process(self, convert_chests=False, quantity=0, interval=900, *args, **kwargs):

        self.log.debug('Running Chest Opener')

        items = self.bot.find_inventory_items([
                inventory.BRONZE_CHEST[0],
                inventory.BRONZE_KEY[0],
                inventory.SILVER_CHEST[0],
                inventory.SILVER_KEY[0],
            ])
        self.log.info(items)

        comboes = [
            (Quest.BRONZE_KEY, inventory.BRONZE_CHEST[0], inventory.BRONZE_KEY[0]),
            (Quest.SILVER_KEY, inventory.SILVER_CHEST[0], inventory.SILVER_KEY[0])
        ]

        def _totals(items):
            return dict([(id, sum([v[1] for v in vals]))
                for id, vals in items.iteritems() if vals])

        totals = _totals(items)
        self.log.debug(totals)

        tainted = False
        for combo in comboes:
            quest_unlocked = True
            quest, chest, key = combo
            num = min(totals.get(chest, 0), totals.get(key, 0))
            chest_name = EmrossWar.ITEM[str(chest)].get('name')

            if convert_chests:
                to_convert = 10 * ((totals.get(chest, 0) - totals.get(key, 0)) / 11)
                self.log.debug(to_convert)

                if to_convert < 1:
                    self.log.info('No need to convert any "{0}"'.format(chest_name))
                else:
                    try:
                        q = [q for q in self.quest_manager.list()
                            if str(q['id']) == quest].pop()
                        self.log.info('Target quest: {0}'.format(q))

                        if q['status'] == 0:
                            self.quest_manager.accept(q['id'])
                    except IndexError:
                        quest_unlocked = False

                    self.log.info('Convert {0}x"{1}"'.format(to_convert, chest_name))
                    while quest_unlocked and to_convert > 0:
                        to_convert -= 1
                        tainted = True
                        self.quest_manager.reward(q['id'])
                        self.quest_manager.accept(q['id'])


            if tainted:
                items.update(self.bot.find_inventory_items([chest, key]))
                totals = _totals(items)

            num = min(totals.get(chest, 0), totals.get(key, 0))
            if num > 0:
                city = self.bot.poorest_city()
            else:
                self.log.info('Unable to open any "{0}" at this point'.format(chest_name))
                continue

            opened = 0
            while opened < num and (quantity == 0 or opened < quantity):
                try:
                    idx = [i for i in items.get(key) if i[1] > 0].pop()
                    idx[1] -= 1
                    opened += 1
                    json = self.bot.item_manager.use(city.id, idx[0])
                    if json['code'] != EmrossWar.SUCCESS:
                        break

                    for rcvd in json['ret']['item']:
                        self.log.info('Got {0}x"{1}" from "{2}"'.format(
                            rcvd['num'], EmrossWar.ITEM[str(rcvd['sid'])].get('name'),
                            chest_name
                        ))
                    self.log.info('Opened {0}x"{1}" so far'.format(opened, chest_name))
                except IndexError:
                    break

        self.sleep(interval)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    from bot import bot

    logger.info(bot.find_inventory_item(inventory.BRONZE_CHEST))

    items = bot.find_inventory_items([
        inventory.BRONZE_CHEST[0],
        inventory.BRONZE_KEY[0],
        inventory.SILVER_CHEST[0],
        inventory.SILVER_KEY[0]
    ])
    logger.info(items)
