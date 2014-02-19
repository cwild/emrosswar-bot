"""
The attack/defense calculations are just the same for NPCs as
they are for players. The NPCs are not in an ally though, so their
modifiers do not gain from this.
"""

class NPCAlliance(object):
    def tech(self, tech, *args, **kwargs):
        return 0

alliance = NPCAlliance()
