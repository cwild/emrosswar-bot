import logging

from emross.api import EmrossWar
from emross.quests import Quest
from emross.utility.base import EmrossBaseObject

EmrossWar.extend('QUEST', 'translation/%(lang)s/quest_data.js')
logger = logging.getLogger(__name__)

class QuestManager(EmrossBaseObject):
    URL = 'game/system_task_api.php'

    def __init__(self, bot):
        super(QuestManager, self).__init__(bot, __name__)

    def list(self):
        self.log.info('List quests')
        json = self.bot.api.call(self.URL, action='task_list')

        if json['code'] == EmrossWar.SUCCESS:
            quests = json['ret']['quest']
            for quest in quests:
                self.log.debug('Quest: "{quest}", Accepted: {accepted}, Done: {done}'.format(
                    quest=EmrossWar.QUEST[str(quest['id'])].get('name', 'Unknown quest'),
                    accepted='yes' if int(quest['status']) else 'no',
                    done='yes' if int(quest['done']) else 'no'
                    )
                )

            return quests

    def accept(self, id):
        self.log.debug('Accepting quest "{0}"'.format(EmrossWar.QUEST[str(id)].get('name')))
        return self.bot.api.call(self.URL, action='task_up', id=id)

    def reward(self, id):
        self.log.debug('Complete quest "{0}"'.format(EmrossWar.QUEST[str(id)].get('name')))
        return self.bot.api.call(self.URL, action='task_end', id=id)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    from bot import bot
    bot.update()

    logger.info(EmrossWar.QUEST.get(Quest.SILVER_KEY))

    quest_manager = QuestManager(bot)
    quests = quest_manager.list()
    for quest in quests:
        if quest['status'] == 0:
            quest_manager.accept(quest['id'])
