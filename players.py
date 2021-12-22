'''Player Logic'''

from utils import SuperPower
from cards import CHINA_CARD, SCORING, EVENT
from board import SpaceRace

class Player:
    
    def __init__(self, superpower):

        self.superpower = SuperPower[superpower]
        self.hand = list()
        self.china_card = 0
        self.space_race = SpaceRace()


    def show_hand(self):
        hand = self.hand[:]

        # we don't store the China Card as an actual card in our hand because
        # for most hand-related situations, it's not treated as being there.
        # (It cannot be discarded, it cannot be Headlined, it doesn't go
        # to the discard after being played... maybe other things.)
        if self.china_card:
            hand.append(CHINA_CARD)

        return hand


    def recieve_cards(self, cards):
        self.hand += cards


    def recieve_china_card(self, available):
        '''The China Card can be recieved in either an available
        or unavailable state.'''
        self.china_card = 1 if available else -1


    def activate_china_card(self):
        '''At the beginning of new turns, a facedown/inactive China Card
        becomes available to play.'''
        self.china_card = 1 if self.china_card else 0


    def remove_china_card(self):
        '''The China Card can be given to the other player.'''
        self.china_card = 0


    def compute_available_actions(self):

        available_actions = []

        for card in self.hand:

            if card._card_class == EVENT:

                # this is our event, or a neutral event, we can *either*:
                # - play the event *OR* 
                # - use for operation points
                if card.alignment.value in (self.superpower.value, 'Neutral'):
                    available_actions += [('PLAY', card), ('OPS', card)]

                # otherwise, we must choose whether we will trigger the event
                # BEFORE or AFTER we use the operation points
                # (technically I think you can play the opponent's events but lol)
                # we might also SPACE RACE this card, if we can.
                # (again, technically we can space our own stuff, but lol)
                else:
                    available_actions += [(('EVENT', card), ('OPS', card)),
                                          (('OPS', card), ('EVENT', card))]

                    if self.space_race.available:
                        available_actions.append(('SPACE', card))

            elif card._card_class == SCORING:

                available_actions.append(('SCORE', card))

            else:

                raise ValueError(card)

        if self.china_card:
            available_actions.append(('OPS', CHINA_CARD))

        return available_actions



US_PLAYER = Player('us')
USSR_PLAYER = Player('ussr')