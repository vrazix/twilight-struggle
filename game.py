'''What runs the actual game itself.'''

from copy import copy

from cards import EARLY_WAR_CARDS, Pile, Card
from board import MAP, Defcon, SpaceRace
from players import US_PLAYER, USSR_PLAYER
from test_toolbox import basic_starting_influence

class GameState:

    def __init__(self, map, cards, us_player, ussr_player):
        
        self.map = map
        self.removed_pile = Pile([], 'Removed from the game')
        self.discard_pile = Pile([], 'Discard')
        self.draw_pile = Pile(cards, 'Draw', self.discard_pile)
        self.us_player = us_player
        self.ussr_player = ussr_player
        self.score = 0
        self.defcon = Defcon()


    def begin_game(self):

        self.draw_pile.shuffle()
        self.us_player.recieve_cards(self.draw_pile.draw(8))
        self.ussr_player.recieve_cards(self.draw_pile.draw(8))
        self.ussr_player.recieve_china_card(available=True)


def expand_coup_actions(card, game_state, player, action_type='COUP'):
    '''For a given card, game_state and player, return all of the legal coup
    actions available. For this enumeration, coup and realignments offer identical choices,
    so calling it again with action_type = 'REALIGN' takes care of this.

    A reminder that coups of battlegrounds are still a legal choice at defcon=2, despite this
    causing thermonuclear war, since this is a valid choice for defcon suicide! This is the same
    reason that we don't filter out coups that cannot possibly change influence, e.g. a
    2 ops card on a 4 stability country (4*2 = 2+6), it *could* be a valid defcon suicide.

    game_state.defcon.defcon_level restricts the legal choices for where you may attempt a coup:
    5: No restriction
    4: Not in Europe
    3: Not in Asia
    2: Not in Middle East
    '''

    assert action_type in ('COUP', 'REALIGN')

    coup_actions = []

    countries = game_state.map.countries

    if game_state.defcon.defcon_level == 5:

        for country in countries.europe().has_enemy_influence(player.superpower):

            coup_actions.append((action_type, card, country))

    if game_state.defcon.defcon_level > 3:

        for country in countries.asia().has_enemy_influence(player.superpower):

            coup_actions.append((action_type, card, country))

    if game_state.defcon.defcon_level > 2:

        for country in countries.middle_east().has_enemy_influence(player.superpower):

            coup_actions.append((action_type, card, country))

    # finally, we *can* always coup any non eu/asia/me location. all BGs will lead to
    # defcon suicide at defcon_level = 2, but this is a valid choice and matters for
    # things like Lone Gunman and CIA Created
    for country in countries.has_enemy_influence(player.superpower).is_not_defcon_restricted():

        coup_actions.append((action_type, card, country))

    return coup_actions


def expand_one_ops_influence(game_state, player):

    pass


def expand_two_ops_influence(game_state, player):

    # start with all the available options for one ops, twice
    # this will include placing 2 influence in a country (in serial, which is fine)
    influence_actions = expand_one_ops_influence(game_state, player) * 2


def expand_influence_actions(card, game_state, player):
    '''For a given card, game_state and player, determine all of the legal placements
    for influence using this card.

    1) You can add to any country you currently have influence in
    2) You can add to any country neighboring a country you have influence in
    3) You can add to any country neighboring your superpower

    A) It costs 1 Ops point to add to a country not controlled by your opponent
    B) It costs 2 Ops points to add to a country controlled by your opponent
    This penalty is checked for *each* influence added, e.g. you might 'break control'
    with the first influence (and spend 2), and then pay only 1 for the remaining.

    We must enumerate all possibilities for the given card's ops_value. For one influence
    point this is mostly easy, any country meeting 1, 2 or 3 not controlled by the
    opponent. For two, we can put one and one in any location not controlled by opp, two in
    any location not controlled by opp OR one in any location controlled by opp.

    For three...'''

    influence_actions = []

    ops_value = card.ops_value

    allocator = {1: expand_one_ops_influence,
                 2: expand_two_ops_influence,
                 3: expand_three_ops_influence,
                 4: expand_four_ops_influence,
                 }


def expand_ops_actions(card, game_state, player):

    ops_actions = []

    # add all coup options
    ops_actions += expand_coup_actions(card, game_state, player)

    # add all realignment options (same as coup, really)
    ops_actions += expand_coup_actions(card, game_state, player, 'REALIGN')

    # add all influence options (uh oh)
    ops_actions += expand_influence_actions(card, game_state, player)


    return ops_actions


def expand_available_actions(action_list, game_state, player):

    expanded_actions = []

    while action_list:

        current_action = action_list.pop()

        # not chained (yet)
        if isinstance(current_action[1], Card):
            action_type, card = current_action

            if action_type == 'OPS':

                expanded_actions += expand_ops_actions(card, game_state, player)

        # chained (e.g., A->B)
        else:
            pass

    return expanded_actions


if __name__ == '__main__':

    gs = GameState(MAP, EARLY_WAR_CARDS, US_PLAYER, USSR_PLAYER)
    gs.begin_game()

    print(MAP)
    print()
    print('USSR Hand:', USSR_PLAYER.show_hand())
    print()
    print('US Hand:', US_PLAYER.show_hand())
    print()

    # TODO: Give players options for starting influence
    basic_starting_influence(MAP)

    USSR_available = USSR_PLAYER.compute_available_actions()
    US_available = US_PLAYER.compute_available_actions()
    print(f'USSR available actions ({len(USSR_available)}):', USSR_available)
    print()
    print(f'US available actions ({len(US_available)}):', US_available)
    print()

    USSR_expanded = expand_available_actions(USSR_available, gs, USSR_PLAYER)
    US_expanded = expand_available_actions(US_available, gs, US_PLAYER)
    print(f'USSR expanded actions ({len(USSR_expanded)}):', USSR_expanded)
    print()
    print(f'US expanded actions ({len(US_expanded)}):', US_expanded)

    #print(gs.map.countries)