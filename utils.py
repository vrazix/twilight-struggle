'''Utils for the game.'''

from enum import Enum
import random


class SuperPower(Enum):
    us = 'US'
    ussr = 'USSR'

    def __invert__(self):
        '''Make ~player.superpower work.'''

        if self.value == 'US':
            return SuperPower['ussr']
        return SuperPower['us']


class d6:
    def __init__(self):
        pass

    def roll(self):
        return random.randint(1, 6)

D6 = d6()