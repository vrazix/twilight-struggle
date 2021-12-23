'''Board and Board Logic'''

from enum import Enum

from cards import ScoringRegion 
from cards import ASIA_SCORING, EUROPE_SCORING, MIDDLE_EAST_SCORING, \
                  CENTRAL_AMERICA_SCORING, SOUTHEAST_ASIA_SCORING, \
                  AFRICA_SCORING, SOUTH_AMERICA_SCORING
from utils import SuperPower, D6
#from players import US_PLAYER, USSR_PLAYER

MAP_US_SP = SuperPower.us
MAP_USSR_SP = SuperPower.ussr

DEFCON_RESTRICTED = (ASIA_SCORING, EUROPE_SCORING, MIDDLE_EAST_SCORING)

class MapRegion(Enum):
    western_eu = 'Western Europe'
    eastern_eu = 'Eastern Europe'
    central_am = 'Central America'
    south_am = 'South America'
    africa = 'Africa'
    middle_east = 'Middle East'
    asia = 'Asia'
    southeast_asia = 'Southeast Asia'


class Country:

    def __init__(self, name, scoring_region, map_regions, neighbors, stability, us_influence=0, ussr_influence=0, battleground=False):
        '''Create a Country object.
        
        Parameters:
        ----------
        name : str
            The name of the country.
        scoring_region : ScoringRegion name
            The scoring region that this country belongs to.
        map_regions : MapRegion name or iterable of MapRegion names
            The map region(s) that this country belongs to.
        neighbors : list of str
            The names of the countries that neighbor this one, may also be
            MAP_US_SP or MAP_USSR_SP for the superpower nodes.
        stability : int, in range(1, 6)
            The stability of this country.
        us_influence : int
            The starting US influence for this country.
        ussr_influence : int
            The starting USSR influence for this country.
        battleground : bool
            Whether or not this country is designated as a battleground country.
            (default False).
        '''

        self.name = name
        self.scoring_region = ScoringRegion[scoring_region]

        try:
            self.map_regions = tuple(MapRegion[map_region] for map_region in map_regions)
        except KeyError:
            self.map_regions = (MapRegion[map_regions],)

        self.neighbors = neighbors

        assert stability in range(1, 6)

        self.stability = stability
        self.us_influence = us_influence
        self.ussr_influence = ussr_influence
        self.battleground = battleground


    def controlled_by(self):
        '''Returns who controls this country, if anyone. Control is obtained
        by having more influence than opponent by the stability or greater.'''

        if self.us_influence - self.ussr_influence >= self.stability:
            return SuperPower.us
        elif self.ussr_influence - self.us_influence >= self.stability:
            return SuperPower.ussr
        else:
            return None


    def has_any_influence(self):
        return bool(self.us_influence + self.ussr_influence)


    def has_enemy_influence(self, enemy):

        if enemy == SuperPower.ussr:
            if self.us_influence > 0:
                return True
        elif enemy == SuperPower.us:
            if self.ussr_influence > 0:
                return True

        return False


    def has_player_influence(self, player):

        if player == SuperPower.us:
            if self.us_influence > 0:
                return True

        if player == SuperPower.ussr:
            if self.ussr_influence > 0:
                return True

        return False


    def is_adjacent_to(self, player):
        '''A country is considered adjacent to a player if:
        1) The country has the player's influence
        2) The country is neighboring the player superpower location
        3) The country neighbors a country with the player's influence.'''

        if player == SuperPower.us:
            if self.us_influence > 0:
                return True

            if MAP_US_SP in self.neighbors:
                return True

        elif player == SuperPower.ussr:
            if self.ussr_influence > 0:
                return True

            if MAP_USSR_SP in self.neighbors:
                return True

        if any(country.has_player_influence(player) if country not in [MAP_US_SP, MAP_USSR_SP] else country == player for country in self.neighbors):
                return True

        return False


    def control_margin(self, player, margin):
        if ~player == SuperPower.us:
            if self.us_influence - self.stability == margin:
                return True
        if ~player == SuperPower.ussr:
            if self.ussr_influence - self.stability == margin:
                return True

        return False


    def __repr__(self):

        return f'{self.name}|{self.us_influence}|{self.ussr_influence}'


class CountryBundle(dict):

    def __init__(self, country_dict):

        assert all(isinstance(country, (Country, SuperPower)) for country in country_dict.values())

        self.update(**country_dict)


    def asia(self):
        return CountryBundle({name: country for name, country in self.items() if country.scoring_region == ASIA_SCORING})


    def europe(self):
        return CountryBundle({name: country for name, country in self.items() if country.scoring_region == EUROPE_SCORING})
    
    
    def middle_east(self):
        return CountryBundle({name: country for name, country in self.items() if country.scoring_region == MIDDLE_EAST_SCORING})
    

    def central_america(self):
        return CountryBundle({name: country for name, country in self.items() if country.scoring_region == CENTRAL_AMERICA_SCORING})


    def southeast_asia(self):
        return CountryBundle({name: country for name, country in self.items() if country.scoring_region == SOUTHEAST_ASIA_SCORING})


    def africa(self):
        return CountryBundle({name: country for name, country in self.items() if country.scoring_region == AFRICA_SCORING})


    def south_america(self):
        return CountryBundle({name: country for name, country in self.items() if country.scoring_region == SOUTH_AMERICA_SCORING})


    def has_any_influence(self):
        return CountryBundle({name: country for name, country in self.items() if country.has_any_influence()})


    def has_enemy_influence(self, enemy):
        return CountryBundle({name: country for name, country in self.items() if country.has_enemy_influence(enemy)})


    def is_battleground(self):
        return CountryBundle({name: country for name, country in self.items() if country.battleground})


    def is_not_battleground(self):
        return CountryBundle({name: country for name, country in self.items() if not country.battleground})


    def is_not_defcon_restricted(self):
        return CountryBundle({name: country for name, country in self.items() if country.scoring_region not in DEFCON_RESTRICTED})


    def is_adjacent_to(self, player):
        return CountryBundle({name: country for name, country in self.items() if country.is_adjacent_to(player)})


    def not_enemy_controlled(self, player):
        return CountryBundle({name: country for name, country in self.items() if country.controlled_by() != ~player})


    def enemy_controlled(self, player):
        return CountryBundle({name: country for name, country in self.items() if country.controlled_by() == ~player})


    def control_margin(self, player, margin):
        return CountryBundle({name: country for name, country in self.items() if country.control_margin(player, margin)})


class Map:

    def __init__(self, countries):

        assert all(isinstance(country, (Country, SuperPower)) for country in countries)

        self.countries = CountryBundle({country.name: country for country in countries})


    def __repr__(self):

        return ', '.join(f'{country}' for country in self.countries.values())


def validate_map(map):
    '''Check that all neighboring connections are reciprocal.'''

    for name, country_obj in map.countries.items():

        for neighbor in country_obj.neighbors:

            if neighbor not in [MAP_US_SP, MAP_USSR_SP]:

                neighbor_obj = map.countries[neighbor]

                assert name in neighbor_obj.neighbors, (name, neighbor_obj.neighbors)


def populate_neighbors(map):
    '''Each country is instantiated with a neighbors attribute that is just the names of the
    neighbor countries. We need to replace this with one that references the Country object directly. 
    We can only do this after the graph is built, of course, since usually the Country objects
    aren't ready at the time we instantiate their neighbors...'''

    for name, country in map.countries.items():

        # leave the superpower objects alone
        country.neighbors = [map.countries[neighbor_name] if neighbor_name not in [MAP_US_SP, MAP_USSR_SP] 
                             else neighbor_name for neighbor_name in country.neighbors]


MAP = Map([# EUROPE
           Country('Canada', 'europe', 'western_eu', ['UK', MAP_US_SP], 4, 2, 0),
           Country('UK', 'europe', 'western_eu', ['Canada', 'Norway', 'Benelux', 'France'], 5, 5, 0),
           Country('Norway', 'europe', 'western_eu', ['UK', 'Sweden'], 4, 0, 0),
           Country('Sweden', 'europe', 'western_eu', ['Norway', 'Denmark', 'Finland'], 4, 0, 0),
           Country('Finland', 'europe', ('western_eu', 'eastern_eu'), ['Sweden', MAP_USSR_SP], 4, 0, 1),
           Country('Denmark', 'europe', 'western_eu', ['Sweden', 'West Germany'], 3, 0, 0),
           Country('Benelux', 'europe', 'western_eu', ['UK', 'West Germany'], 3, 0, 0),
           Country('West Germany', 'europe', 'western_eu', ['Denmark', 'Benelux', 'France', 'East Germany', 'Austria'], 4, 0, 0, True),
           Country('East Germany', 'europe', 'eastern_eu', ['West Germany', 'Poland', 'Czechoslovakia', 'Austria'], 3, 0, 3, True),
           Country('Poland', 'europe', 'eastern_eu', ['East Germany', 'Czechoslovakia', MAP_USSR_SP], 3, 0, 0, True),
           Country('Czechoslovakia', 'europe', 'eastern_eu', ['East Germany', 'Poland', 'Hungary'], 3, 0, 0),
           Country('France', 'europe', 'western_eu', ['UK', 'West Germany', 'Italy', 'Spain/Portugal', 'Algeria'], 3, 0, 0, True),
           Country('Spain/Portugal', 'europe', 'western_eu', ['France', 'Italy', 'Morocco'], 2, 0, 0),
           Country('Italy', 'europe', 'western_eu', ['Spain/Portugal', 'France', 'Austria', 'Yugoslavia', 'Greece'], 2, 0, 0, True),
           Country('Austria', 'europe', ('western_eu', 'eastern_eu'), ['West Germany', 'East Germany', 'Hungary', 'Italy'], 4, 0, 0),
           Country('Hungary', 'europe', 'eastern_eu', ['Czechoslovakia', 'Romania', 'Yugoslavia', 'Austria'], 3, 0, 0),
           Country('Yugoslavia', 'europe', 'eastern_eu', ['Hungary', 'Romania', 'Greece', 'Italy'], 3, 0, 0),
           Country('Romania', 'europe', 'eastern_eu', ['Hungary', 'Turkey', 'Yugoslavia', MAP_USSR_SP], 3, 0, 0),
           Country('Turkey', 'europe', 'western_eu', ['Romania', 'Greece', 'Bulgaria', 'Syria'], 2, 0, 0),
           Country('Greece', 'europe', 'western_eu', ['Italy', 'Yugoslavia', 'Turkey', 'Bulgaria'], 2, 0, 0),
           Country('Bulgaria', 'europe', 'eastern_eu', ['Greece', 'Turkey'], 3, 0, 0),
           # AFRICA
           Country('Algeria', 'africa', 'africa', ['France', 'Tunisia', 'Saharan States', 'Morocco'], 2, 0, 0, True),
           Country('Morocco', 'africa', 'africa', ['Spain/Portugal', 'Algeria', 'West African States'], 3, 0, 0),
           Country('Tunisia', 'africa', 'africa', ['Libya', 'Algeria'], 2, 0, 0),
           Country('Saharan States', 'africa', 'africa', ['Algeria', 'Nigeria'], 1, 0, 0),
           Country('Nigeria', 'africa', 'africa', ['Saharan States', 'Ivory Coast', 'Cameroon'], 1, 0, 0, True),
           Country('West African States', 'africa', 'africa', ['Morocco', 'Ivory Coast'], 2, 0, 0),
           Country('Ivory Coast', 'africa', 'africa', ['West African States', 'Nigeria'], 2, 0, 0),
           Country('Cameroon', 'africa', 'africa', ['Nigeria', 'Zaire'], 1, 0, 0),
           Country('Zaire', 'africa', 'africa', ['Cameroon', 'Angola', 'Zimbabwe'], 1, 0, 0, True),
           Country('Angola', 'africa', 'africa', ['Zaire', 'Botswana', 'South Africa'], 1, 0, 0, True),
           Country('South Africa', 'africa', 'africa', ['Angola', 'Botswana'], 3, 1, 0, True),
           Country('Botswana', 'africa', 'africa', ['South Africa', 'Angola', 'Zimbabwe'], 2, 0, 0),
           Country('Zimbabwe', 'africa', 'africa', ['Zaire', 'Botswana', 'SE African States'], 1, 0, 0),
           Country('SE African States', 'africa', 'africa', ['Zimbabwe', 'Kenya'], 1, 0, 0),
           Country('Kenya', 'africa', 'africa', ['SE African States', 'Somalia'], 2, 0, 0),
           Country('Somalia', 'africa', 'africa', ['Kenya', 'Ethiopia'], 2, 0, 0),
           Country('Ethiopia', 'africa', 'africa', ['Somalia', 'Sudan'], 1, 0, 0),
           Country('Sudan', 'africa', 'africa', ['Ethiopia', 'Egypt'], 1, 0, 0),
           # MIDDLE EAST
           Country('Syria', 'middle_east', 'middle_east', ['Turkey', 'Israel', 'Lebanon'], 2, 0, 1),
           Country('Israel', 'middle_east', 'middle_east', ['Syria', 'Lebanon', 'Jordan', 'Egypt'], 4, 1, 0, True),
           Country('Egypt', 'middle_east', 'middle_east', ['Libya', 'Israel', 'Sudan'], 2, 0, 0, True),
           Country('Libya', 'middle_east', 'middle_east', ['Egypt', 'Tunisia'], 2, 0, 0, True),
           Country('Lebanon', 'middle_east', 'middle_east', ['Syria', 'Israel', 'Jordan'], 1, 0, 0),
           Country('Jordan', 'middle_east', 'middle_east', ['Israel', 'Lebanon', 'Saudi Arabia', 'Iraq'], 2, 0, 0),
           Country('Saudi Arabia', 'middle_east', 'middle_east', ['Jordan', 'Iraq', 'Gulf States'], 3, 0, 0, True),
           Country('Gulf States', 'middle_east', 'middle_east', ['Iraq', 'Saudi Arabia'], 3, 0, 0),
           Country('Iraq', 'middle_east', 'middle_east', ['Gulf States', 'Iran', 'Jordan', 'Saudi Arabia'], 3, 0, 1, True),
           Country('Iran', 'middle_east', 'middle_east', ['Iraq', 'Afganistan', 'Pakistan'], 2, 1, 0, True),
           # ASIA
           Country('Afganistan', 'asia', 'asia', ['Iran', 'Pakistan', MAP_USSR_SP], 2, 0, 0),
           Country('Pakistan', 'asia', 'asia', ['Afganistan', 'Iran', 'India'], 2, 0, 0, True),
           Country('India', 'asia', 'asia', ['Pakistan', 'Burma'], 3, 0, 0, True),
           Country('Burma', 'asia', ('asia', 'southeast_asia'), ['India', 'Laos/Cambodia'], 2, 0, 0),
           Country('Laos/Cambodia', 'asia', ('asia', 'southeast_asia'), ['Burma', 'Vietnam', 'Thailand'], 1, 0, 0),
           Country('Vietnam', 'asia', ('asia', 'southeast_asia'), ['Laos/Cambodia', 'Thailand'], 1, 0, 0),
           Country('Thailand', 'asia', ('asia', 'southeast_asia'), ['Laos/Cambodia', 'Vietnam', 'Malaysia'], 2, 0, 0, True),
           Country('Malaysia', 'asia', ('asia', 'southeast_asia'), ['Thailand', 'Australia', 'Indonesia'], 2, 0, 0),
           Country('Australia', 'asia', 'asia', ['Malaysia'], 4, 4, 0),
           Country('Indonesia', 'asia', ('asia', 'southeast_asia'), ['Malaysia', 'Phillipines'], 1, 0, 0),
           Country('Phillipines', 'asia', ('asia', 'southeast_asia'), ['Indonesia', 'Japan'], 2, 1, 0),
           Country('Japan', 'asia', 'asia', ['Phillipines', 'South Korea', 'Taiwan', MAP_US_SP], 4, 1, 0, True),
           Country('Taiwan', 'asia', 'asia', ['Japan', 'South Korea'], 3, 0, 0),
           Country('South Korea', 'asia', 'asia', ['Japan', 'Taiwan', 'North Korea'], 3, 1, 0, True),
           Country('North Korea', 'asia', 'asia', ['South Korea', MAP_USSR_SP], 3, 0, 3, True),
           # CENTRAL AMERICA
           Country('Mexico', 'central_am', 'central_am', [MAP_US_SP, 'Guatemala'], 2, 0, 0, True),
           Country('Guatemala', 'central_am', 'central_am', ['Mexico', 'El Salvador', 'Honduras'], 1, 0, 0),
           Country('El Salvador', 'central_am', 'central_am', ['Guatemala', 'Honduras'], 1, 0, 0),
           Country('Honduras', 'central_am', 'central_am', ['Guatemala', 'El Salvador', 'Nicaragua', 'Costa Rica'], 2, 0, 0),
           Country('Nicaragua', 'central_am', 'central_am', ['Cuba', 'Honduras', 'Costa Rica'], 1, 0, 0),
           Country('Cuba', 'central_am', 'central_am', [MAP_US_SP, 'Nicaragua', 'Haiti'], 3, 0, 0, True),
           Country('Haiti', 'central_am', 'central_am', ['Cuba', 'Dominican Republic'], 1, 0, 0),
           Country('Dominican Republic', 'central_am', 'central_am', ['Haiti'], 1, 0, 0),
           Country('Costa Rica', 'central_am', 'central_am', ['Nicaragua', 'Honduras', 'Panama'], 3, 0, 0),
           Country('Panama', 'central_am', 'central_am', ['Costa Rica', 'Columbia'], 2, 1, 0, True),
           # SOUTH AMERICA
           Country('Columbia', 'south_am', 'south_am', ['Panama', 'Ecuador', 'Venezuela'], 1, 0, 0),
           Country('Venezuela', 'south_am', 'south_am', ['Columbia', 'Brazil'], 2, 0, 0, True),
           Country('Brazil', 'south_am', 'south_am', ['Venezuela', 'Uruguay'], 2, 0, 0, True),
           Country('Uruguay', 'south_am', 'south_am', ['Brazil', 'Paraguay', 'Argentina'], 2, 0, 0),
           Country('Argentina', 'south_am', 'south_am', ['Uruguay', 'Chile', 'Paraguay'], 2, 0, 0, True),
           Country('Paraguay', 'south_am', 'south_am', ['Argentina', 'Uruguay', 'Bolivia'], 2, 0, 0),
           Country('Bolivia', 'south_am', 'south_am', ['Peru', 'Paraguay'], 2, 0, 0),
           Country('Chile', 'south_am', 'south_am', ['Argentina', 'Peru'], 3, 0, 0, True),
           Country('Peru', 'south_am', 'south_am', ['Chile', 'Bolivia', 'Ecuador'], 2, 0, 0),
           Country('Ecuador', 'south_am', 'south_am', ['Columbia', 'Peru'], 2, 0, 0),
           ])

validate_map(MAP)
populate_neighbors(MAP)


class Defcon:

    def __init__(self):

        self.defcon_level = 5


    def set_defcon_to(self, n):
        self.defcon_level = n


    def decrease_defcon(self):
        '''Decreases defcon_level and returns True if thermonuclear war has been triggered.'''

        self.defcon_level -= 1

        return True if self.defcon_level < 2 else False


    def increase_defcon(self):
        self.defcon_level += 1


class SpaceRace:

    def __init__(self):

        self.progress = 0
        self.available = True
        self.spaced_once = False
        self.minimum_ops = 2
        self.space_twice = False


    def reset_for_turn(self):
        if self.progress < 8:
            self.available = True
            self.spaced_once = False


    def activate_space_twice(self):
        self.space_twice = True


    def attempt_space(self, opponent_progress):
        '''Handle the Space Race action. Roll a D6 and check against
        the `less_than` table (dictionary) to determine success.

        Parameters:
        ----------
        opponent_progress : int
            The opponent's progress on the space race track, which is used
            to determine the vps_gained.

        Returns:
        ----------
        success : bool
            Whether or not advancing the track was successful.
        vps_gained : int
            Number of VPs gained (0 if unsuccessful).
        reward : TODO lol
            Some kind of signifier for how to change the gamestate, idk.
        '''

        assert self.available

        # progress: roll requirement
        less_than = {0: 4,
                     1: 5,
                     2: 4,
                     3: 5,
                     4: 4,
                     5: 5,
                     6: 4,
                     7: 3,
                     }

        # progress: (if 1st, if 2nd)
        vps = {1: (2, 1),
               2: (0, 0),
               3: (2, 0),
               4: (0, 0),
               5: (3, 1),
               6: (0, 0),
               7: (4, 2),
               8: (2, 0),
               }

        # progress: reward
        # TODO: figure out wtf these should actually be
        reward = {1: None,
                  2: activate_space_twice,
                  3: None,
                  4: 'OPPONENT_SPACE_TWICE_REWARD',
                  5: None,
                  6: 'DISCARD_ONE_CARD_REWARD',
                  7: None,
                  8: 'EIGHT_ACTIONS_REWARD',
                  }

        success = D6.roll() < less_than[self.progress]

        if success:

            # move up, get vp based on opponent's progress (are we 1st or 2nd to get this far)
            self.progress += 1
            vp_selector = 0 if opponent_progress < self.progress else 1
            vps_gained = vps[self.progress][vp_selector]

            if self.progress == 2:
                reward[self.progress]()
                reward_return = None
            else:
                reward_return = reward[self.progress]

            # the minimum ops required can change moving up the track
            if self.progress == 4:
                self.minimum_ops = 3
            if self.progress == 7:
                self.minimum_ops = 4

        else:
            vps_gained = 0
            reward_return = None

        # if we're at the end of the track, we're done!
        # normally you can only space race a card once
        # UNLESS you have the space_twice ability
        # then we need to know if you spaced before...
        if self.progress == 8:
                self.available = False
        elif not self.space_twice:
                self.available = False
        else:
            if self.spaced_once:
                self.available = False
            else:
                self.spaced_once = True

        return success, vps_gained, reward_return