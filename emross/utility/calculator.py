from __future__ import division
import math

from emross.alliance import AllyTech
from emross.arena.hero import Gear, Hero
from emross.military.camp import SoldierStat, SOLDIER_STAT_MODIFIERS
from emross.research.studious import Study
from emross.utility.base import EmrossBaseObject


HALL_CONTRIBUTIONS = {
    AllyTech.BATTLECRY: 0.01,
    AllyTech.TENACITY: 0.05,
    AllyTech.TOUGHNESS: 0.01,
    AllyTech.VALOR: 0.05,
}


class WarCalculator(EmrossBaseObject):

    def defense(self, hero, troops={}, ally=None, **kwargs):
        """
        Calculate the precise amount of defense a hero and his troops will have.

        =(basedef * (0.005 + 0.00025 * (AdvArmor + DefFormation))
                  * (200 + ROUNDUP(HeroDef * (1 + 0.05 * HallTenacity)))
              * (1 + HallToughness/100))
              + HeroChestArmor
        """

        _ally = ally or self.bot.alliance

        soldier_data = self.bot.cities[0].barracks.soldier_data

        hero_defense = 0
        hero_armour = 0

        if hero:
            hero_defense = hero.stat(Hero.DEFENSE)
            try:
                hero_armour = hero.gear[Gear.ARMOR_SLOT]['item']['attr'][Gear.TROOP_DEFENSE]
            except (IndexError, KeyError):
                pass

        tenacity = 1 + _ally.tech(AllyTech.TENACITY) * HALL_CONTRIBUTIONS.get(AllyTech.TENACITY, 0)

        hero_contribution = 200 + math.ceil(hero_defense * tenacity)

        research = self.bot.builder.task(Study)
        troop_defense = []

        for troop, qty in troops.iteritems():
            troop_data = soldier_data(troop)

            total = (troop_data[SoldierStat.DEFENSE] * qty)
            total *= hero_contribution
            total *= (1 + _ally.tech(AllyTech.TOUGHNESS) * HALL_CONTRIBUTIONS.get(AllyTech.TOUGHNESS, 0))

            func = SOLDIER_STAT_MODIFIERS.get(troop, {}).get(SoldierStat.DEFENSE)
            if func:
                total = func(total, research.get_tech_level)

            troop_defense.append(int(math.floor(total)))

        return sum(troop_defense) + hero_armour


    def attack(self, hero, troops={}, ally=None, **kwargs):
        """
        Calculate the attack range given the hero and its army.
        From minimum attack to maximum possible.

        =baseattk * (0.0005 + 0.000025 * (AdvWeapon + AttkFormation))
                  * (200+ ROUNDUP(HeroAttk* (1 + 0.05 * HallValor)))
                  * (1 + HallBattleCry/100)
        """
        _ally = ally or self.bot.alliance
        soldier_data = self.bot.cities[0].barracks.soldier_data

        hero_attack = 0
        if hero:
            hero_attack = hero.stat(Hero.ATTACK)

        valor = 1 + _ally.tech(AllyTech.VALOR) * HALL_CONTRIBUTIONS.get(AllyTech.VALOR, 0)

        hero_contribution = 200 + math.ceil(hero_attack * valor)

        research = self.bot.builder.task(Study)
        min_attack, max_attack = [], []

        for troop, qty in troops.iteritems():
            troop_data = soldier_data(troop)

            total = (troop_data[SoldierStat.ATTACK] * qty)
            total *= hero_contribution
            total *= (1 + _ally.tech(AllyTech.BATTLECRY) * HALL_CONTRIBUTIONS.get(AllyTech.BATTLECRY, 0))

            func = SOLDIER_STAT_MODIFIERS.get(troop, {}).get(SoldierStat.ATTACK)
            if func:
                total = func(total, research.get_tech_level)

            min_attack.append(int(math.floor(total)))
            max_attack.append(int(math.floor(total * \
                (troop_data[SoldierStat.CRITICAL]/100)
            )))

        return sum(min_attack), sum(max_attack)
