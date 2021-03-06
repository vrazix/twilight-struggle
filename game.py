'''What runs the actual game itself.'''

import itertools

from cards import Pile, Card, USSR_EVENT, US_EVENT, NEUTRAL_EVENT, SCORING
from cards import EARLY_WAR_CARDS, MID_WAR_CARDS, LATE_WAR_CARDS
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
        self.turn = 0 # 0 for setup, otherwise actual
        self.action_round = 0 # 0 for headline, otherwise actual
        self.total_action_rounds = 6
        self.phasing_player = ussr_player
        self.hand_size = 8

        # various flags for card events
        self.IRON_LADY_PLAYED = False
        self.USSR_SEASIA_BONUS_OP = False
        self.CAMP_DAVID_ACCORDS_PLAYED = False
        self.WARSAW_PACT_PLAYED = False
        self.DEGAULLE_PLAYED = False
        self.MARSHALL_PLAN_PLAYED = False
        self.NATO_PLAYED = False
        self.CONTAINMENT = False
        self.US_JAPAN_MUTUAL = False
        self.RED_SCARE = False
        self.RED_PURGE = False
        self.NORAD_ACTIVE = False


    def swap_phasing(self):

        if self.phasing_player == self.us_player:
            self.phasing_player = self.ussr_player
        elif self.phasing_player == self.ussr_player
            self.phasing_player = self.us_player
        else:
            assert False, self.phasing_player


    def execute_choices(self, card=None, ops_value=0, influence=False, 
                        realign=False, coup=False, countries=None):
        '''Basic choice executer for the current phasing player. If an Event object
        is passed, then the phasing player remains the same but the Event's alignment
        is used to determine the executing player.

        Parameters:
        ----------
        card : Event object or None (default None)
            This executes the event by the event's alignment player or the phasing
            player if the event is neutral.
        ops_value : int (default 0)
            Ops value with which to execute operation-point value choices. Different
            from the card in case of any modifiers.
        influence : bool (default False)
            Allow the player to place influence, potentially restricted by `countries`.
        realign : bool (default False)
            Allow the player to execute realignments, potentially restricted by
            `countries`.
        coup : bool (default False)
            Allow the player to execute a coup, potentially restricted by `countries`.
        countries : CountryBundle or None (default None)
            If given, the subset of countries available for the operations. If None,
            all countries are available.
        '''

        # game end only possible via event or coup

        game_end = False

        if card:

            game_end = self.execute_card_choice(card)

        elif ops_value > 0:

            if influence:

                self.execute_influence_choice(ops_value, countries)

            elif realign:

                self.execute_realignment_choice(ops_value, countries)

            elif coup:

                game_end = execute_coup_choice(ops_value, countries)

            else:

                raise ValueError(f'Positive ops value but no operations selected (influence={influence}, realign={realign}, coup={coup}).')

        else:

            raise ValueError(f'No card ({card}) and non positive ops value ({ops_value}).')

        return game_end


    def execute_card_choice(self, card):
        '''Execute the card Event.

        Returns the game_end state (True for Game Over)'''

        if card.alignment == USSR_EVENT:

            # record the current phasing player so we may reset
            # to them after executing the USSR event
            prior_phasing = self.phasing_player
            self.phasing_player = self.ussr_player

            # call the card's function
            game_end = card.func(self)

            self.phasing_player = prior_phasing

        elif card.alignment == US_EVENT:

            prior_phasing = self.phasing_player
            self.phasing_player = self.us_player

            game_end = card.func(self)

            self.phasing_player = self.prior_phasing

        elif card.alignment == NEUTRAL_EVENT:

            game_end = card.func(self)

        else:
            # the only other possibility should be a Scoring Card
            assert card._card_class == SCORING

            game_end = card.func(self)

        return game_end


    def begin_new_turn(self):

        if self.turn == 10:
            end_game_scoring(self)

        self.turn += 1

        print(f'Begin Turn {self.turn}.')

        if self.turn == 4:

            self.hand_size += 1
            self.total_action_rounds += 1
            self.draw_pile.cards += MID_WAR_CARDS
            self.draw_pile.shuffle()

        if self.turn == 8:

            self.draw_pile.cards += LATE_WAR_CARDS
            self.draw_pile.shuffle()

        self.reset_turn_only_flags()

        # both players draw up to the current hand size
        us_hand_size = len(self.us_player.hand)
        ussr_hand_size = len(self.ussr_player.hand)

        us_to_draw = self.hand_size - us_hand_size
        ussr_to_draw = self.hand_size - ussr_hand_size

        # TODO: Actual alternating draws so that reshuffles aren't biased

        self.us_player.recieve_cards(self.draw_pile.draw(us_to_draw))
        self.ussr_player.recieve_cards(self.draw_pile.draw(ussr_to_draw))


    def begin_game(self, player_setup=False):
        '''Shuffle the draw pile, deal each player 8 cards and give
        the USSR player the china card.'''

        self.draw_pile.shuffle()
        self.ussr_player.recieve_china_card(available=True)
        self.begin_new_turn()

        if player_setup:
            # ussr (starting phasing player) distributes 6 influence in eastern europe
            execute_choices(ops_value=6, countries=self.map.eastern_eu())
            self.swap_phasing()

            # us distributes 7 in western europe
            execute_choices(ops_value=7, countries=self.map.western_eu())

            # typical setup, US distributes two anywhere they have influence
            us_countries = self.map.has_player_influence(self.phasing_player.superpower)
            execute_choices(ops_value=2, countries=us_countries)

            self.swap_phasing()

        else:

            basic_starting_influence(self.map)


    def reset_game(self, cards):
        '''Reset player's hands and game piles. Put `cards` in the draw pile.
        Reshuffle and redeal starting hands.'''

        self.us_player.empty_hand()
        self.us_player.remove_china_card()
        self.ussr_player.empty_hand()
        self.ussr_player.remove_china_card()
        
        self.removed_pile = Pile([], 'Removed from the game')
        self.discard_pile = Pile([], 'Discard')
        self.draw_pile = Pile(cards, 'Draw', self.discard_pile)
        
        self.begin_game()


    def reset_turn_only_flags(self):
        '''Reset all flags that only last a turn.'''
        self.USSR_SEASIA_BONUS_OP = False
        self.CONTAINMENT = False
        self.RED_PURGE = False
        self.RED_SCARE = False


    def run_game(self, player_setup=False):
        '''Commence and maintain the game until it ends.'''

        # draws starting hands, does beginning influence
        self.begin_game(player_setup)
        assert self.phasing_player == self.ussr_player, (self.phasing_player, self.ussr_player)

        while True:

            while True:

                if self.action_round == 0:

                    self.run_headline_phase()

                elif self.action_round > self.total_action_rounds:

                    break

                else:

                    self.run_action_round(self.ussr_player)
                    self.run_action_round(self.us_player)

                self.action_round += 1

            begin_new_turn()


    def run_headline_phase(self):
        '''Execute headline phase.

        1) Both players pick a card in their hand to headline
            This is normally done simultaneously, but here we'll juse use USSR->US
        2) Compare ops_value, higher goes first
            If a tie, US player goes first
        3) Resolve Events (or Scoring)
        '''
        pass


    def run_action_round(self, player):
        '''Let player do their action round.'''

        pass


def end_game_scoring(gamestate):
    '''Compute final score.'''
    pass


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

    As such, all countries with influence in Africa/South America/Central America are always
    valid targets (CountryBundle.is_not_defcon_restricted()).
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


def expand_one_ops_influence(card, game_state, player):
    '''With one ops, we can add one influence to any country which:
    1) We are adjacent to
    2) Is not enemy controlled
    '''

    adjacent = game_state.map.countries.not_enemy_controlled(player.superpower).is_adjacent_to(player.superpower)

    influence_actions = [('INFLUENCE', card, country, 1) for country in adjacent]

    return influence_actions


def expand_two_ops_influence(card, game_state, player):
    '''With two ops, we can add either:
    1) One influence to legal spaces followed by one influence in legal spaces
        This is combinations of 2 with replacement e.g. cwr(ABC, 2):
        - AA, AB, AC, BB, BC, CC

    2) One influence to enemy controlled spaces
    '''

    # start with all the available options for one ops "twice" (combinations with replacement)
    # this will include placing 2 influence in a country (in serial, which is fine)
    one_ops = expand_one_ops_influence(card, game_state, player)
    influence_actions = list(itertools.combinations_with_replacement(one_ops, 2))

    # now add all of the opponent's controlled countries, which we can add 1 influence to
    enemy_controlled = game_state.map.countries.enemy_controlled(player.superpower)
    influence_actions += [('INFLUENCE', card, country, 1) for country in enemy_controlled]

    return influence_actions


def expand_three_ops_influence(card, game_state, player):
    '''With three ops, we can add either:
    1) One influence to legal spaces x3 (see expand_two_ops_influence)

    2) One influence to an enemy controlled space + One influence to a legal space

    3) Two influence to an space controlled by exactly the stability number
        e.g. Spain/Portugal (2) has two US influence. We can place 1 to break control,
        which costs 2 influence points, and then place a second.
    '''

    # start with all available options for one ops "thrice"
    one_ops = expand_one_ops_influence(card, game_state, player)
    influence_actions = list(itertools.combinations_with_replacement(one_ops, 3))

    # where we can add one influence to an enemy controlled space, and then anywhere else
    enemy_controlled = game_state.map.countries.enemy_controlled(player.superpower)
    add_enemy_controlled = [('INFLUENCE', card, country, 1) for country in enemy_controlled]
    enemy_one_and_one_elsewhere = []
    for add_one_to_enemy in add_enemy_controlled:
        for one_op in one_ops:
            enemy_one_and_one_elsewhere.append((add_one_to_enemy, one_op))
    influence_actions += enemy_one_and_one_elsewhere

    # where we can add two influence to an enemy controlled space
    # possible where the first will break control, i.e. where enemy influence == stability
    barely_controlled = enemy_controlled.control_margin(player.superpower, 0)
    influence_actions += [('INFLUENCE', card, country, 2) for country in barely_controlled]

    return influence_actions


def expand_four_ops_influence(card, game_state, player):
    '''With four ops we can...
    1) One influence to legal spaces x4 (see expand_two_ops_influence)

    2) One influence to an enemy controlled space + one influence to legal spaces x2

    3) One influence to an enemy controlled space over controlled x2
        This captures two influence to overcontrolled countries
    '''

    # as usual, one ops but "fourfold"
    one_ops = expand_one_ops_influence(card, game_state, player)
    influence_actions = list(itertools.combinations_with_replacement(one_ops, 4))

    # we can do one enemy controlled space and then one ops twice
    enemy_controlled = game_state.map.countries.enemy_controlled(player.superpower)

    add_enemy_controlled = [('INFLUENCE', card, country, 1) for country in enemy_controlled]
    enemy_one_and_two_elsewhere = []
    for add_one_to_enemy in add_enemy_controlled:
        for one_op in itertools.combinations_with_replacement(one_ops, 2):
            enemy_one_and_two_elsewhere.append((add_one_to_enemy, one_op))

    influence_actions += enemy_one_and_two_elsewhere

    # we can do two to regions that are overcontrolled
    over_controlled = enemy_controlled.over_controlled(player.superpower)
    add_over_controlled = [('INFLUENCE', card, country, 1) for country in over_controlled]
    influence_actions += list(itertools.combinations_with_replacement(add_over_controlled, 2))

    return influence_actions


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

    # TODO: Add logic for China Card-like bonuses, e.g. if all of the allocated influence
    # is in Asia, an extra choice in Asia is available

    influence_actions = []

    ops_value = card.ops_value

    allocator = {1: expand_one_ops_influence,
                 2: expand_two_ops_influence,
                 3: expand_three_ops_influence,
                 4: expand_four_ops_influence,
                 }

    return allocator[ops_value](card, game_state, player)


def expand_ops_actions(card, game_state, player):

    ops_actions = []

    # add all coup options
    ops_actions += expand_coup_actions(card, game_state, player)

    # add all realignment options (same as coup, really)
    ops_actions += expand_coup_actions(card, game_state, player, 'REALIGN')

    # add all influence options (uh oh)
    ops_actions += expand_influence_actions(card, game_state, player)


    return ops_actions


def expand_play_actions(card, game_state, player):

    allocator = {''}


def expand_available_actions(action_list, game_state, player):

    expanded_actions = []

    while action_list:

        current_action = action_list.pop()

        # not chained (yet)
        if isinstance(current_action[1], Card):
            action_type, card = current_action

            if action_type == 'OPS':

                expanded_actions += expand_ops_actions(card, game_state, player)

            # unchanged
            elif action_type == 'SCORE':

                expanded_actions += current_action

            elif action_type == 'PLAY':

                #expanded_actions += expand_play_actions(card, game_state, player)
                pass

        # chained (e.g., A->B), always involves opponent's event
        else:
            # so what's annoying about this is it represents a jump in the chain
            # we will have 'PLAY' (opponent choices) -> 'OPS' (our choices)
            # or 'OPS' (our choices) -> 'PLAY' (opponent choices)
            # it is 100% possible that the choices available for the second
            # are dependent on the first, so the calculation needs to be done later!
            # but right now i have no mechanism for adding to the monte carlo tree
            # ahead of 'now'.

            # so, we'll just add what we can.
            for ordered_action in current_action:
                if action_type == 'PLAY':

                    expanded_actions += ('PASS FOR OPPONENT PLAY', card)

                elif action_type == 'OPS':

                    expanded_actions += expand_ops_actions(card, game_state, player)

    return expanded_actions


if __name__ == '__main__':

    gs = GameState(MAP, EARLY_WAR_CARDS, US_PLAYER, USSR_PLAYER)
    gs.begin_game()
    basic_starting_influence(MAP)

    print(MAP)
    print()
    print('USSR Hand:', USSR_PLAYER.show_hand())
    print()
    print('US Hand:', US_PLAYER.show_hand())
    print()

    # TODO: Give players options for starting influence

    USSR_available = USSR_PLAYER.compute_available_actions()
    US_available = US_PLAYER.compute_available_actions()
    print(f'USSR available actions ({len(USSR_available)}):', USSR_available)
    print()
    print(f'US available actions ({len(US_available)}):', US_available)
    print()

    USSR_expanded = expand_available_actions(USSR_available, gs, USSR_PLAYER)
    US_expanded = expand_available_actions(US_available, gs, US_PLAYER)
    print(f'USSR expanded actions ({len(USSR_expanded)}):')#, USSR_expanded)
    print()
    print(f'US expanded actions ({len(US_expanded)}):')#, US_expanded)

    print('Four ops possibilities for influence by USSR with:', EARLY_WAR_CARDS[-5])
    four_ops = expand_four_ops_influence(EARLY_WAR_CARDS[-5], gs, USSR_PLAYER)
    print(len(four_ops))
    #for _ in four_ops[:10]:
    #    print(_)

    #print(gs.map.countries)