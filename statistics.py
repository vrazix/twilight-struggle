'''Computing rough statistics for the AI choices.'''

from matplotlib import pyplot as plt
import numpy as np

from game import GameState, expand_available_actions
from cards import EARLY_WAR_CARDS, Pile, Card
from board import MAP, Defcon, SpaceRace
from players import US_PLAYER, USSR_PLAYER
from test_toolbox import basic_starting_influence, worst_case_influence

ussr_choices = []
us_choices = []


gs = GameState(MAP, EARLY_WAR_CARDS, US_PLAYER, USSR_PLAYER)
gs.begin_game()
basic_starting_influence(MAP)
#worst_case_influence(MAP)
print(MAP)

for _ in range(1000):
    
    USSR_available = USSR_PLAYER.compute_available_actions()
    US_available = US_PLAYER.compute_available_actions()

    USSR_expanded = expand_available_actions(USSR_available, gs, USSR_PLAYER)
    US_expanded = expand_available_actions(US_available, gs, US_PLAYER)

    ussr_choices.append(len(USSR_expanded))
    us_choices.append(len(US_expanded))

    print(_, len(USSR_expanded), len(US_expanded))

    gs.reset_game(EARLY_WAR_CARDS)

bins = np.linspace(0, max(ussr_choices+us_choices), 100)
plt.hist(ussr_choices, bins, alpha=0.5, label='ussr action space')
plt.hist(us_choices, bins, alpha=0.5, label='us action space')
plt.xlabel('Choices on T1')
plt.title('State-space complexity')
plt.legend(loc='upper right')
plt.show()