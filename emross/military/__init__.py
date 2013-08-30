from emross.api import EmrossWar

"""
Each race has it's own slightly different Soldier data. It differs only in the
description but that may change one day; let's do it right from the start!
"""
for i in range(1,4):
    EmrossWar.extend('SOLDIER_{0}'.format(i), 'translation/%(lang)s/soldier{0}_data.js'.format(i))
del i
