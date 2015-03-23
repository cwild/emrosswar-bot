from emross import mobs
mobs.commanders = [
    mobs.Hero('ChaosLord', attack=30, defense=15)
]
mobs.units = [
    mobs.Unit('Horror', mobs.DevilArmy.FIVE_STAR),
    mobs.Unit('Horror', mobs.DevilArmy.SIX_STAR, attack=15, defense=8, critical=180),
    mobs.Unit('Nightmare', mobs.DevilArmy.SIX_STAR),
    mobs.Unit('Nitemare', mobs.DevilArmy.SIX_STAR, attack=40, defense=12, critical=317.5),
    mobs.Unit('Inferno', mobs.DevilArmy.SEVEN_STAR, attack=120, defense=40, critical=362.5),
    mobs.Unit('Inferno', mobs.DevilArmy.EIGHT_STAR, attack=120, defense=40, critical=120),

    mobs.Unit('', mobs.DevilArmy.SEVEN_STAR, alias='Inferno'),
    mobs.Unit('', mobs.DevilArmy.EIGHT_STAR, alias='Inferno'),

    mobs.Unit('Infantry', mobs.Colony.LARGE_FARM, attack=15, defense=10, health=100),
]
