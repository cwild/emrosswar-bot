from emross.api import EmrossWar
from emross.item.item import ItemRank, ItemType
from emross.research.studious import Study
from emross.research.tech import Tech
from emross.resources import Resource
from emross.structures.buildings import Building
from emross.structures.construction import Construct
from emross.utility.task import Task

class AutoEnhance(Task):
    INTERVAL = 300
    ENHANCEABLE_ITEMS = [
        ItemType.WEAPON,
        ItemType.ARMOR,
        ItemType.MOUNT,
        ItemType.RING,
        ItemType.BOOK
    ]

    def process(self,
        enhance_thresholds=[(95, 10000000), (75, 6000000), (40, 2000000)],
        enhance_items=ENHANCEABLE_ITEMS,
        enhance_ranks=[ItemRank.BLESSED, ItemRank.RARE],
        minimum_enhance=0,
        *args, **kwargs):


        if self.bot.pvp:
            self.sleep(86400)
            return True

        if len(self.bot.cities) == 0:
            self.sleep(1)
            return True

        # Find highest level university
        construction = self.bot.builder.task(Construct)
        city =  max(self.bot.cities, key=lambda city: \
                construction.structure_level(city, Building.UNIVERSITY))

        level_uni = construction.structure_level(city, Building.UNIVERSITY)
        if level_uni == 0:
            self.log.debug('No university at this castle, unable to proceed')
            return True

        # Calculate the highest enhancement level possible at this university
        study = self.bot.builder.task(Study)
        enhance = int(study.tech_level(city, Tech.ENHANCEMENT) / 3)
        max_level = level_uni
        if level_uni == 30 and enhance > 0:
            max_level += enhance

        self.log.info('Highest level {0} ({1}) is at "{2}" and can enhance to +{3}'.format(
            EmrossWar.BUILDING[str(Building.UNIVERSITY)].get('name'),
            level_uni,
            city.name,
            max_level
        ))

        # Collect all the enhanceable items together
        items = []
        cooldown = 0
        success_rate = 0

        for _type in enhance_items:
            json = self.bot.item_manager.list_enhance(_type)
            if json['code'] == EmrossWar.SUCCESS:
                cooldown = int(json['ret']['cd'])
                success_rate = int(json['ret']['per'])
                for item in json['ret']['item']:
                    if int(EmrossWar.ITEM[str(item['sid'])]['rank']) \
                        in enhance_ranks and item['up'] >= minimum_enhance:
                        items.append(item)


        items.sort(key = lambda i: i.get('sid'))
        items.sort(key = lambda i: [ i.get('up'), i.get('p')], reverse=True)

        for count, item in enumerate(items, start=1):
            self.log.info('{0}: {name} (+{enhance}), {cost}'.format(count,
                name=EmrossWar.ITEM[str(item['sid'])]['name'],
                enhance=item['up'],
                cost=item['p']
            ))

        if cooldown == 0:
            done = False
            for percent, maximum_cost in enhance_thresholds:
                if done:
                    break

                if success_rate < percent:
                    self.log.debug('Success rate too low: target {0}%, current {1}%'.format(\
                        percent, success_rate))
                    continue

                self.log.info('Item search: Enhance ({0}%), Maximum cost: {1}'.format(\
                    success_rate, maximum_cost))

                for item in items:
                    if item['up'] < max_level and item['p'] <= maximum_cost and \
                    city.resource_manager.meet_requirements({Resource.GOLD: item['p']}, **kwargs):
                        json = self.bot.item_manager.upgrade(city, item['id'])

                        if json['code'] == EmrossWar.SUCCESS:
                            res = json['ret']
                            cooldown = res[1]
                            name = EmrossWar.ITEM[str(item['sid'])]['name']

                            if int(res[0]) == 1:
                                self.log.info('Successfully enhanced "{0}" to +{1}!'.format(\
                                    name, res[4]))
                            else:
                                self.log.info('The attempted enhance of "{0}"({1}) has FAILED.'.format(\
                                    name, item['up']))

                            city.update()
                            done = True
                            break

            # Outside of loop, sanity check
            if not done:
                self.log.debug('Cooldown is already 0 but we have not managed to enhance anything')
                self.sleep(self.INTERVAL)
                return True

        self.sleep(cooldown)
