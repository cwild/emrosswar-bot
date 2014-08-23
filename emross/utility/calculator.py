from __future__ import division
import copy
import math

from emross.alliance import AllyTech
from emross.arena.hero import Gear, Hero
from emross.military.camp import SoldierStat, DEFAULT_SOLDIER_STAT_MODIFIERS, SOLDIER_STAT_MODIFIERS
from emross.research.studious import Study
from emross.utility.base import EmrossBaseObject

from lib import six


HALL_CONTRIBUTIONS = {
    AllyTech.BATTLECRY: 0.01,
    AllyTech.TENACITY: 0.05,
    AllyTech.TOUGHNESS: 0.01,
    AllyTech.VALOR: 0.05,
}


class WarCalculator(EmrossBaseObject):
    # If no SOLDIER_STAT_MODIFIERS are set for a given troop, use the default one
    ASSUME_DEFAULT_SOLDIER_STATS = True
    HERO_BASE_MODIFIER = 200
    BATTLE_ROUNDS = 3

    def defense(self, hero, troops={}, ally=None, soldier_data=None,
                hero_base=HERO_BASE_MODIFIER,
                assume_default_soldier_stats=None, **kwargs):
        """
        Calculate the precise amount of defense a hero and his troops will have.

        =(basedef * (0.005 + 0.00025 * (AdvArmor + DefFormation))
                  * (200 + ROUNDUP(HeroDef * (1 + 0.05 * HallTenacity)))
              * (1 + HallToughness/100))
              + HeroChestArmor
        """
        if assume_default_soldier_stats is None:
            assume_default_soldier_stats = self.ASSUME_DEFAULT_SOLDIER_STATS
        _ally = ally or self.bot.alliance
        soldier_data = soldier_data or self.bot.cities[0].barracks.soldier_data

        hero_defense = 0
        hero_armour = 0

        if hero:
            hero_defense = hero.stat(Hero.DEFENSE)
            try:
                hero_armour = hero.gear[Gear.ARMOR_SLOT]['item']['attr'][Gear.TROOP_DEFENSE]
            except (IndexError, KeyError):
                pass

        tenacity = 1 + _ally.tech(AllyTech.TENACITY) * HALL_CONTRIBUTIONS.get(AllyTech.TENACITY, 0)

        hero_contribution = hero_base + math.ceil(hero_defense * tenacity)

        research = self.bot.builder.task(Study)
        troop_defense = []

        for troop, qty in troops.iteritems():
            troop_data = soldier_data(troop)

            if not len(troop_data):
                raise ValueError('Unable to find soldier data for "{0}"'.format(troop))

            total = (troop_data[SoldierStat.DEFENSE] * qty)
            total *= hero_contribution or 1

            total *= (1 + _ally.tech(AllyTech.TOUGHNESS) * HALL_CONTRIBUTIONS.get(AllyTech.TOUGHNESS, 0))

            func = SOLDIER_STAT_MODIFIERS.get(troop, DEFAULT_SOLDIER_STAT_MODIFIERS if assume_default_soldier_stats else {}).get(SoldierStat.DEFENSE)
            if func:
                total = func(total, research.get_tech_level)

            troop_defense.append(int(math.floor(total)))

        return sum(troop_defense) + hero_armour


    def attack(self, hero, troops={}, ally=None, soldier_data=None,
                hero_base=HERO_BASE_MODIFIER,
                assume_default_soldier_stats=None, **kwargs):
        """
        Calculate the attack range given the hero and its army.
        From minimum attack to maximum possible.

        =baseattk * (0.0005 + 0.000025 * (AdvWeapon + AttkFormation))
                  * (200+ ROUNDUP(HeroAttk* (1 + 0.05 * HallValor)))
                  * (1 + HallBattleCry/100)
        """
        if assume_default_soldier_stats is None:
            assume_default_soldier_stats = self.ASSUME_DEFAULT_SOLDIER_STATS
        _ally = ally or self.bot.alliance
        soldier_data = soldier_data or self.bot.cities[0].barracks.soldier_data

        hero_attack = 0
        if hero:
            hero_attack = hero.stat(Hero.ATTACK)

        valor = 1 + _ally.tech(AllyTech.VALOR) * HALL_CONTRIBUTIONS.get(AllyTech.VALOR, 0)

        hero_contribution = hero_base + math.ceil(hero_attack * valor)

        research = self.bot.builder.task(Study)
        min_attack, max_attack = [], []

        for troop, qty in troops.iteritems():
            troop_data = soldier_data(troop)

            if not len(troop_data):
                raise ValueError('Unable to find soldier data for "{0}"'.format(troop))

            total = (troop_data[SoldierStat.ATTACK] * qty)
            total *= hero_contribution or 1
            total *= (1 + _ally.tech(AllyTech.BATTLECRY) * HALL_CONTRIBUTIONS.get(AllyTech.BATTLECRY, 0))

            func = SOLDIER_STAT_MODIFIERS.get(troop, DEFAULT_SOLDIER_STAT_MODIFIERS if assume_default_soldier_stats else {}).get(SoldierStat.ATTACK)
            if func:
                total = func(total, research.get_tech_level)

            min_attack.append(int(math.floor(total)))
            max_attack.append(int(math.floor(total * \
                (troop_data[SoldierStat.CRITICAL]/100)
            )))

        return sum(min_attack), sum(max_attack)

    def health(self, troops, soldier_data=None, **kwargs):
        soldier_data = soldier_data or self.bot.cities[0].barracks.soldier_data
        total = 0

        for troop, qty in troops.iteritems():
            try:
                total += qty * soldier_data(troop)[SoldierStat.HEALTH]
            except TypeError:
                pass

        return int(math.floor(total))

    def troops_to_defend_attack(self, troop, required_defense, hero, ally=None,
        soldier_data=None, hero_base=HERO_BASE_MODIFIER,
        assume_default_soldier_stats=None, **kwargs):
        """
        Calculate how many of the given soldier type would be required
        to defend the target_attack
        """
        if assume_default_soldier_stats is None:
            assume_default_soldier_stats = self.ASSUME_DEFAULT_SOLDIER_STATS
        total = 0

        _ally = ally or self.bot.alliance
        soldier_data = soldier_data or self.bot.cities[0].barracks.soldier_data

        hero_defense = 0
        hero_armour = 0

        if hero:
            hero_defense = hero.stat(Hero.DEFENSE)
            try:
                hero_armour = hero.gear[Gear.ARMOR_SLOT]['item']['attr'][Gear.TROOP_DEFENSE]
            except (IndexError, KeyError):
                pass

        tenacity = 1 + _ally.tech(AllyTech.TENACITY) * HALL_CONTRIBUTIONS.get(AllyTech.TENACITY, 0)

        hero_contribution = hero_base + math.ceil(hero_defense * tenacity)

        research = self.bot.builder.task(Study)

        troop_data = soldier_data(troop)

        if not len(troop_data):
            raise ValueError('Unable to find soldier data for "{0}"'.format(troop))

        total = troop_data[SoldierStat.DEFENSE]
        total *= hero_contribution or 1

        total *= (1 + _ally.tech(AllyTech.TOUGHNESS) * HALL_CONTRIBUTIONS.get(AllyTech.TOUGHNESS, 0))

        func = SOLDIER_STAT_MODIFIERS.get(troop, DEFAULT_SOLDIER_STAT_MODIFIERS if assume_default_soldier_stats else {}).get(SoldierStat.DEFENSE)
        if func:
            total = func(total, research.get_tech_level)

        total = int(math.floor(total))

        # Round-up the number of required units!
        return int(math.ceil((required_defense-hero_armour) / total))

    def battle_simulator(self, contestant1, contestant2, rounds=None, soldier_data=None):
        soldier_data = soldier_data or self.bot.cities[0].barracks.soldier_data

        c1 = copy.deepcopy(contestant1)
        c2 = copy.deepcopy(contestant2)

        _rounds = 0
        while True:
            if rounds and  _rounds >= (rounds or self.BATTLE_ROUNDS):
                break

            _rounds += 1

            c1_attack, c1_max_attack = self.attack(**c1)
            c1_defense = self.defense(**c1)
            self.log.debug(six.u('contestant1: defense={0}, min_attack={1}, max_attack={2}').format(
                c1_defense, c1_attack, c1_max_attack
            ))

            c2_attack, c2_max_attack = self.attack(**c2)
            c2_defense = self.defense(**c2)
            self.log.debug(six.u('contestant2: defense={0}, min_attack={1}, max_attack={2}').format(
                c2_defense, c2_attack, c2_max_attack
            ))

            armies = [
                (c1_attack, c2_defense, c2['troops'], c2.get('soldier_data')),
                (c2_attack, c1_defense, c1['troops'], c1.get('soldier_data'))
            ]

            for catt, odef, otroops, opp_data in armies:
                delta = catt - odef
                if delta <= 0:
                    continue

                _soldier_data = opp_data or soldier_data

                for troop, qty in otroops.iteritems():
                    defense = _soldier_data(troop)[SoldierStat.DEFENSE]
                    health = _soldier_data(troop)[SoldierStat.HEALTH]

                    try:
                        killed = math.floor(delta / health)
                    except TypeError:
                        # Seems better than nothing..
                        killed = math.floor(delta / defense)

                    otroops[troop] -= killed

                for k in list(otroops.keys()):
                    if otroops[k] < 1:
                        del otroops[k]

            yield _rounds, c1['troops'], c2['troops']

            if not all([c1['troops'], c2['troops']]):
                break
