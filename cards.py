'''Cards and Card Logic'''

import random
from enum import Enum

from utils import D6

class CardType(Enum):
    china_card = -1
    scoring = 0
    event = 1

CHINA_CARD = CardType.china_card
SCORING = CardType.scoring
EVENT = CardType.event


class EventAlignment(Enum):
    ussr = 'USSR'
    neutral = 'Neutral'
    us = 'US'

USSR_EVENT = EventAlignment.ussr
NEUTRAL_EVENT = EventAlignment.neutral
US_EVENT = EventAlignment.us


class ScoringRegion(str, Enum):
    asia = 'Asia'
    europe = 'Europe'
    middle_east = 'Middle East'
    central_am = 'Central America'
    southeast_asia = 'Southeast Asia'
    africa = 'Africa'
    south_am = 'South America'

ASIA_SCORING = ScoringRegion.asia
EUROPE_SCORING = ScoringRegion.europe
MIDDLE_EAST_SCORING = ScoringRegion.middle_east
CENTRAL_AMERICA_SCORING = ScoringRegion.central_am
SOUTHEAST_ASIA_SCORING = ScoringRegion.southeast_asia
AFRICA_SCORING = ScoringRegion.africa
SOUTH_AMERICA_SCORING = ScoringRegion.south_am


class CardDestination(Enum):
    discard = 'discard'
    rfg = 'rfg'
    other = 'other'


class Card:
    '''Generic card object.'''
    _card_class: CardType

    def __init__(self, name, ops_value, text, star=False):
        '''Create a Card object.
        
        Parameters:
        ----------
        name : str
            Name of the card
        ops_value : int, in range(5)
            Operations value of the card. Determines strength of card when played
            for operations as well as headline resolution order.
        text : str
            Rules and reminder text for the card.
        star : bool, optional
            Designates the card as a 'star' type, which means it is removed from
            the game after it resolves. Adds a '*' to the repr as a reminder.
            (default False).
        '''

        assert ops_value in range(5)

        self.name = name
        self.ops_value = ops_value
        self.text = text
        self.star = star

    def __repr__(self):

        star = '*' if self.star else ''

        return f'{self.name}{star}'


CHINA_CARD = Card('The China Card', 4, 'The China Card')


class ScoringCard(Card):
    _card_class = SCORING

    def __init__(self, region):
        self.scoring_region = ScoringRegion[region]
        text = f'{self.scoring_region.value} Scoring Card'

        # only the Southeast Asia scoring card is a star event, so a simple check for that.
        super().__init__(text, 0, text, self.scoring_region == 'Southeast Asia')


class Event(Card):
    _card_class = EVENT

    def __init__(self, name, func, ops_value, alignment, text, star=False):

        self.alignment = EventAlignment[alignment]
        self.func = func

        super().__init__(name, ops_value, text, star)

    def __call__(self, *args):
        self.func(*args)


class Pile:

    def __init__(self, cards, name, refill_pile=None):
        '''A pile of cards.
        
        Parameters:
        ----------
        cards : iterable of Card objects
            Starting cards in this pile.
        name : str
            Name of this pile, e.g. "USSR Player's Hand", "Draw Deck"
        refill_pile : Pile or None
            Where this pile will refill itself from if it runs out.
            (Default None).
        '''

        self.cards = list(cards)
        self.name = name
        self.refill_pile = None


    def shuffle(self):
        random.shuffle(self.cards)


    def empty(self):
        self.cards = []


    def draw(self, n=1):
        '''Draw cards from this pile.

        Draws one at a time, if this pile becomes empty and we have a
        refill pile, this pile will become that pile (shuffled) before
        continuing.'''

        drawn_cards = []

        for d in range(n):

            try:

                card = self.cards.pop()

            except IndexError:

                if self.refill_pile:
                    self.cards = self.refill_pile.cards[:]
                    self.shuffle()
                    self.refill_pile.empty()

                    card = self.cards.pop()

                else:
                    print(f'No more cards in {self.name} to draw, no refill pile.')
                    return None

            drawn_cards.append(card)

        return drawn_cards


    def __repr__(self):

        return f'{self.name} pile containing {len(self.cards)} cards.'


def game_end(gamestate):
    '''Returns True if the game is over (defcon thermonuclear war, score beyond |20|)
    '''

    if gamestate.score > 20 or gamestate.score < -20:
        return True

    if gamestate.defcon.defcon_level == 1:
        return True

    return False


def check_game_end(func):
    '''Attempting a decorator function that will check game over status after
    each event, since Events are the major triggers for such a thing.'''

    def inner(gamestate, *args, **kw):

        output = func(gamestate, *args, **kw)

        return game_end(gamestate)

    return inner


@check_game_end
def Duck_and_Cover(gamestate):
    ''''Degrade the DEFCON level by 1. The US receives VP equal to 5 minus the current DEFCON level.'''
    
    '''Execute Duck and Cover event:
    1) degrade defcon by 1
    2) check end game
    3) score += 5 - defcon.defcon_level
    '''

    new_defcon, thermo_nuclear = gamestate.defcon.decrease_defcon()

    if thermo_nuclear:
        return True

    gamestate.score += 5 - new_defcon

    return False


@check_game_end
def Five_Year_Plan(gamestate):
    '''The USSR must randomly discard a card. If the card has a US associated Event, the Event occurs immediately. If the card has a USSR associated Event or an Event applicable to both players, then the card must be discarded without triggering the Event.'''

    '''Execute Five Year Plan Event.
    1) Attempt to discard a card from USSR player at random.
        a) if can't, exit False
        b) if event is US, trigger Event
        c) otherwise, exit with triggered result'''

    discard = gamestate.ussr_player.discard_at_random()

    if discard:
        if discard.alignment == EventAlignment.us:
            result = discard.event.func(gamestate)
        else:
            return False
    else:
        return False

    return result


@check_game_end
def Socialist_Governments(gamestate):
    '''Remove a total of 3 US Influence from any countries in Western Europe (removing no 
    more than 2 Influence per country). This Event cannot be used after the 
    “#83 – The Iron Lady” Event has been played.

    Execute Socialist Governments Event.
    0) Check for IRON_LADY_PLAYED flag.
    1) Allow USSR to remove 3 US influence anywhere in Western Europe, no more than 2 per
    '''

    if gamestate.IRON_LADY_PLAYED:
        return False

    # ???
    return False


@check_game_end
def Fidel(gamestate):
    '''Remove all US Influence from Cuba. USSR adds sufficient Influence in Cuba for Control.

    Execute Fidel Event.
    1) Set Cuba US influence to 0
    2) Set Cuba USSR influence = Stability
    '''

    cuba = gamestate.map['Cuba']

    cuba.us_influence = 0
    cuba.ussr_influence = cuba.stability

    return False


@check_game_end
def Vietnam_Revolts(gamestate):
    '''Add 2 USSR Influence to Vietnam. For the remainder of the turn, the USSR receives 
    +1 Operations to the Operations value of a card that uses all its Operations in 
    Southeast Asia.

    Execute Vietnam Revolts Event.
    1) Add 2 USSR influence to Vietnam.
    2) Set USSR_SEASIA_BONUS_OP flag.'''

    gamestate.map['Vietnam'].ussr_influence += 2
    gamestate.USSR_SEASIA_BONUS_OP = True

    return False


@check_game_end
def Blockade(gamestate):
    '''Unless the US immediately discards a card with an Operations value of 3 or more, 
    remove all US Influence from West Germany.

    Execute Blockade Event.
    1) Check if US has any =>3 Ops cards
        a) If yes, they must decide which to discard (if any)
        b) If no or fail to, set WG US Influence to 0'''

    west_germany = gamestate.map['West Germany']
    
    if not any(card.ops_value >= 3 for card in gamestate.us_player.hand):

        west_germany.us_influence = 0

    else:
        # TODO: what.
        #raise_choice()
        pass

    return False


@check_game_end
def Korean_War(gamestate):
    '''North Korea invades South Korea. Roll a die and subtract (-1) from the die roll 
    for every US controlled country adjacent to South Korea. On a modified die roll 
    of 4-6, the USSR receives 2 VP and replaces all US Influence in South Korea with 
    USSR Influence. The USSR adds 2 to its Military Operations Track.

    Execute Korean War Event.
    1) Calulate modifier (-1 for each adjacent US controlled country)
    2) Check for success
        a) if so, +2 VPs, replace US inf with USSR inf (set US to 0)
        b) if fail, do nothing
    3) Add 2 to USSR Mil Ops'''

    south_korea = gamestate.map['South Korea']

    modifier = 0

    for neighbor in south_korea.neighbors:
        if neighbor.controlled_by == SuperPower.us:
            modifier -= 1

    roll_result = D6.roll() + modifier

    if roll_result >= 4:

        gamestate.score += 2
        us_inf = south_korea.us_influence
        south_korea.ussr_influence += us_inf
        south_korea.us_influence = 0

    gamestate.ussr_player.mil_ops += 2

    return False


@check_game_end
def Romanian_Abdication(gamestate):
    '''Remove all US Influence from Romania. The USSR adds sufficient Influence to 
    Romania for Control.'''

    romania = gamestate.map['Romania']

    romania.us_influence = 0
    romania.ussr_influence = romania.stability

    return False


@check_game_end
def Arab_Israeli_War(gamestate):
    '''Pan-Arab Coalition invades Israel. Roll a die and subtract (-1) from the die roll 
    for Israel, if it is US controlled, and for every US controlled country adjacent 
    to Israel. On a modified die roll of 4-6, the USSR receives 2 VP and replaces all 
    US Influence in Israel with USSR Influence. The USSR adds 2 to its Military 
    Operations Track. This Event cannot be used after the “#65 – Camp David Accords” Event 
    has been played.

    Execute Arab-Israeli War Event.
    0) Fail if CAMP_DAVID_ACCORDS_PLAYED flag is set
    1) Calculate modifier (-1 for US control of Israel and adjacent countries)
    2) Check for success'''

    if gamestate.CAMP_DAVID_ACCORDS_PLAYED:
        return False

    israel = gamestate.map['Israel']

    modifier = 0

    if israel.controlled_by == SuperPower.us:
        modifier -= 1
    for neighbor in israel.neighbors:
        if neighbor.controlled_by == SuperPower.us:
            modifier -= 1

    roll_result = D6.roll() + modifier

    if roll_result >= 4:

        gamestate.score += 2
        us_inf = israel.us_influence
        israel.ussr_influence += us_inf
        israel.us_influence = 0

    gamestate.ussr_player.mil_ops += 2

    return False                 


@check_game_end
def Comecon(gamestate):
    '''Add 1 USSR Influence to each of 4 non-US controlled countries of Eastern Europe.
    
    Execute Comecon Event.'''

    # TODO: more of this
    #raise_choice()

    pass


@check_game_end
def Nasser(gamestate):
    '''Add 2 USSR Influence to Egypt. The US removes half, rounded up, of its 
    Influence from Egypt.'''

    egypt = gamestate.map['Egypt']

    egypt.ussr_influence += 2
    us_inf = egypt.us_influence
    egypt.us_influence -= us_inf // 2

    return False


@check_game_end
def Warsaw_Pact_Formed(gamestate):
    '''Remove all US influence from 4 countries in Eastern Europe or add 5 USSR 
    Influence to any countries in Eastern Europe (adding no more than 2 Influence
    per country). This Event allows the “#21 – NATO” card to be played as an Event.

    Execute Warsaw Pact Formed Event.
    0) Set WARSAW_PACT_PLAYED flag
    1) USSR player either
        a) Removes all US influence from 4 Eastern European countries
        b) Adds 5 USSR influence, no more than 2 per, in Eastern European countries
    '''

    gamestate.WARSAW_PACT_PLAYED = True

    # TODO: how
    #raise_choice()

    return False


@check_game_end
def De_Gaulle_Leads_France(gamestate):
    '''Remove 2 US Influence from France and add 1 USSR Influence to France. 
    This Event cancels the effect(s) of the “#21 – NATO” Event for France only.'''

    gamestate.DEGAULLE_PLAYED = True

    france = gamestate.map['France']
    france.us_influence -= 2
    france.ussr_influence += 1
                   
    return False


@check_game_end
def Captured_Nazi_Scientist(gamestate):
    '''Move the Space Race Marker ahead by 1 space.'''

    # who is playing this? who is playing *any* event ...
    pass
    


@check_game_end
def Truman_Doctrine(gamestate):
    '''Remove all USSR Influence from a single uncontrolled country in Europe.
    '''

    # TODO: choices...
    pass


@check_game_end
def Olympic_Games(gamestate):
    '''This player sponsors the Olympics. The opponent must either participate or boycott. 
    If the opponent participates, each player rolls a die and the sponsor adds 2 to their roll. 
    The player with the highest modified die roll receives 2 VP (reroll ties). If the opponent 
    boycotts, degrade the DEFCON level by 1 and the sponsor may conduct Operations as if 
    they played a 4 Ops card.

    Execute Olympic Games Event.
    1) Ask opponent to participate or boycott
        a) Boycott: Degrade Defcon, player conducts 4 Ops
        b) Participate, D6+2 vs D6
            i) 2VP to winner'''

    # TODO: many choices
                  
    pass


@check_game_end
def NATO(gamestate):
    '''The USSR cannot make Coup Attempts or Realignment rolls against any US controlled 
    countries in Europe. US controlled countries in Europe cannot be attacked by play of 
    the “#36 – Brush War” Event. This card requires prior play of either the 
    “#16 – Warsaw Pact Formed” or “#23 – Marshall Plan” Event(s) in order to be played 
    as an Event.

    Execute NATO Event.
    0) Check for WARSAW_PACT_PLAYED or MARSHALL_PLAN_PLAYED, if not, exit
    1) Set NATO_PLAYED flag'''

    if WARSAW_PACT_PLAYED or MARSHALL_PLAN_PLAYED:
        gamestate.NATO_PLAYED = True
        return True

    return False


@check_game_end
def Independent_Reds(gamestate):
    '''Add US Influence to either Yugoslavia, Romania, Bulgaria, Hungary, or Czechoslovakia 
    so that it equals the USSR Influence in that country.'''

    # TODO: choices.
    pass                   


@check_game_end
def Marshall_Plan(gamestate):
    '''Add 1 US Influence to each of any 7 non-USSR controlled countries in Western Europe. 
    This Event allows the “#21 – NATO” card to be played as an Event.
    '''

    # TODO: choichie
    gamestate.MARSHALL_PLAN_PLAYED = True
    pass


@check_game_end
def Indo_Pakistani_War(gamestate):
    '''India invades Pakistan or vice versa (player’s choice). Roll a die and subtract (-1) 
    from the die roll for every enemy controlled country adjacent to the target of the 
    invasion (India or Pakistan). On a modified die roll of 4-6, the player receives 2 VP 
    and replaces all the opponent’s Influence in the target country with their Influence. 
    The player adds 2 to its Military Operations Track.

    Execute Indo-Pakistani War Event.
    0) Pick target country
    1) Calulate modifier (-1 for each adjacent enemy controlled country)
    2) Check for success
        a) if so, +2 VPs, replace enemy inf with player inf
        b) if fail, do nothing
    3) Add 2 to player Mil Ops'''

    # TODO:
    # target_country_name = choice()
    # TODO: who is phasing player

    target_country = gamestate.map[target_country_name]

    modifier = 0

    for neighbor in target_country.neighbors:
        if neighbor.controlled_by == SuperPower.us: # TODO: enemy
            modifier -= 1

    roll_result = D6.roll() + modifier

    if roll_result >= 4:

        # TODO: whomst
        gamestate.score += 2
        us_inf = target_country.us_influence
        target_country.ussr_influence += us_inf
        target_country.us_influence = 0

    #gamestate.ussr_player.mil_ops += 2
                   
    pass


@check_game_end
def Containment(gamestate):
    '''All Operations cards played by the US, for the remainder of this turn, receive +1 
    to their Operations value (to a maximum of 4 Operations per card).'''
                   
    gamestate.CONTAINMENT = True

    return True


@check_game_end
def CIA_Created(gamestate):
    '''The USSR reveals their hand of cards for this turn. The US may use the Operations 
    value of this card to conduct Operations.'''

    print(gamestate.ussr_player.show_hand())

    # TODO: US choice *USSR is still phasing player* (e.g. defcon suicide must work)
                   
    pass


@check_game_end
def US_Japan_Mutual(gamestate):
    '''The US adds sufficient Influence to Japan for Control. The USSR cannot make 
    Coup Attempts or Realignment rolls against Japan.'''

    japan = gamestate.map['Japan']
    japan.us_influence = japan.stability + japan.ussr_influence

    gamestate.US_JAPAN_MUTUAL = True

    return True


@check_game_end
def Suez_Crisis(gamestate):
    '''Remove a total of 4 US Influence from France, the United Kingdom and Israel 
    (removing no more than 2 Influence per country).'''

    # TODO: choice.
                  
    pass


@check_game_end
def East_European_Unrest(gamestate):
    '''Early or Mid War: Remove 1 USSR Influence from 3 countries in Eastern Europe. 
    Late War: Remove 2 USSR Influence from 3 countries in Eastern Europe.'''

    if gamestate.turn < 8:
        # TODO: choice
        pass
    else:
        # TODO: different choice
        pass


@check_game_end
def Decolonization(gamestate):
    '''Add 1 USSR Influence to each of any 4 countries in Africa and/or Southeast Asia.'''

    # TODO: Choice.
    pass


@check_game_end
def Red_Scare_Purge(gamestate):
    '''All Operations cards played by the opponent, for the remainder of this turn, 
    receive -1 to their Operations value (to a minimum value of 1 Operations point)'''

    if gamestate.phasing_player == SuperPower.us:
        self.RED_SCARE = True
    elif gamestate.phasing_player == SuperPower.ussr:
        self.RED_PURGE = True
    else:
        raise ValueError(f'Illegal phasing_player {gamestate.phasing_player}.')
                   
    pass


@check_game_end
def UN_Intervention(gamestate, event_card):
    '''Play this card simultaneously with a card containing an opponent’s associated Event. 
    The opponent’s associated Event is canceled but you may use the Operations value of 
    the opponent’s card to conduct Operations. This Event cannot be played during the 
    Headline Phase.'''

    # TODO: uhh
                  
    pass


@check_game_end
def The_Cambridge_Five(gamestate):
    '''The US reveals all scoring cards in their hand of cards. The USSR player may add 
    1 USSR Influence to a single Region named on one of the revealed scoring cards. 
    This card can not be played as an Event during the Late War.'''

    if gamestate.turn > 7:
        return False

    if any(card._card_class == SCORING for card in gamestate.us_player.hand):
        # TODO: USSR picks country in region of any scoring card...
        pass
        return True

    else:

        print('No scoring cards in US player\'s hand.')
        return True


@check_game_end
def Special_Relationship(gamestate):
    '''Add 1 US Influence to a single country adjacent to the U.K. if the U.K. is 
    US-controlled but NATO is not in effect. Add 2 US Influence to a single country 
    in Western Europe, and the US gains 2 VP, if the U.K. is US-controlled and 
    NATO is in effect.'''

    uk = gamestate.map['UK']

    if uk.controlled_by() == SuperPower.us:

        if gamestate.NATO_PLAYED:

            gamestate.score -= 2
            # TODO: choice 2 US influence in Western Europe
        else:

            # TODO: choice 1 US influence in uk.neighbors
            pass

    else:
        print('UK not controlled by US player')
                   
    pass


@check_game_end
def NORAD(gamestate):
    '''Add 1 US Influence to a single country containing US Influence, at the end of 
    each Action Round, if Canada is US-controlled and the DEFCON level moved to 2 
    during that Action Round. This Event is canceled by the “#42 – Quagmire” Event.'''

    gamestate.NORAD_ACTIVE = True

    return True
                  


EARLY_WAR_CARDS = (ScoringCard('asia'), 
                   ScoringCard('europe'),
                   ScoringCard('middle_east'),
                   Event('Duck and Cover', Duck_and_Cover, 3, 'us', 'Degrade the DEFCON level by 1. The US receives VP equal to 5 minus the current DEFCON level.'),
                   Event('Five Year Plan', Five_Year_Plan, 3, 'us', 'The USSR must randomly discard a card. If the card has a US associated Event, the Event occurs immediately. If the card has a USSR associated Event or an Event applicable to both players, then the card must be discarded without triggering the Event.'),
                   Event('Socialist Governments', Socialist_Governments, 3, 'ussr', 'Remove a total of 3 US Influence from any countries in Western Europe (removing no more than 2 Influence per country). This Event cannot be used after the “#83 – The Iron Lady” Event has been played.'),
                   Event('Fidel', Fidel, 2, 'ussr', 'Remove all US Influence from Cuba. USSR adds sufficient Influence in Cuba for Control.', True),
                   Event('Vietnam Revolts', Vietnam_Revolts, 2, 'ussr', 'Add 2 USSR Influence to Vietnam. For the remainder of the turn, the USSR receives +1 Operations to the Operations value of a card that uses all its Operations in Southeast Asia.', True),
                   Event('Blockade', Blockade, 1, 'ussr', 'Unless the US immediately discards a card with an Operations value of 3 or more, remove all US Influence from West Germany.', True),
                   Event('Korean War', Korean_War, 2, 'ussr', 'North Korea invades South Korea. Roll a die and subtract (-1) from the die roll for every US controlled country adjacent to South Korea. On a modified die roll of 4-6, the USSR receives 2 VP and replaces all US Influence in South Korea with USSR Influence. The USSR adds 2 to its Military Operations Track.', True),
                   Event('Romanian Abdication', Romanian_Abdication, 1, 'ussr', 'Remove all US Influence from Romania. The USSR adds sufficient Influence to Romania for Control.', True),
                   Event('Arab-Israeli War', Arab_Israeli_War, 2, 'ussr', 'Pan-Arab Coalition invades Israel. Roll a die and subtract (-1) from the die roll for Israel, if it is US controlled, and for every US controlled country adjacent to Israel. On a modified die roll of 4-6, the USSR receives 2 VP and replaces all US Influence in Israel with USSR Influence. The USSR adds 2 to its Military Operations Track. This Event cannot be used after the “#65 – Camp David Accords” Event has been played.'),
                   Event('Comecon', Comecon, 3, 'ussr', 'Add 1 USSR Influence to each of 4 non-US controlled countries of Eastern Europe.', True),
                   Event('Nasser', Nasser, 1, 'ussr', 'Add 2 USSR Influence to Egypt. The US removes half, rounded up, of its Influence from Egypt.', True),
                   Event('Warsaw Pact Formed', Warsaw_Pact_Formed, 3, 'ussr', 'Remove all US influence from 4 countries in Eastern Europe or add 5 USSR Influence to any countries in Eastern Europe (adding no more than 2 Influence per country). This Event allows the “#21 – NATO” card to be played as an Event.', True),
                   Event('De Gaulle Leads France', De_Gaulle_Leads_France, 3, 'ussr', 'Remove 2 US Influence from France and add 1 USSR Influence to France. This Event cancels the effect(s) of the “#21 – NATO” Event for France only.', True),
                   Event('Captured Nazi Scientist', Captured_Nazi_Scientist, 1, 'neutral', 'Move the Space Race Marker ahead by 1 space.', True),
                   Event('Truman Doctrine', Truman_Doctrine, 1, 'us', 'Remove all USSR Influence from a single uncontrolled country in Europe.', True),
                   Event('Olympic Games', Olympic_Games, 2, 'neutral', 'This player sponsors the Olympics. The opponent must either participate or boycott. If the opponent participates, each player rolls a die and the sponsor adds 2 to their roll. The player with the highest modified die roll receives 2 VP (reroll ties). If the opponent boycotts, degrade the DEFCON level by 1 and the sponsor may conduct Operations as if they played a 4 Ops card.'),
                   Event('NATO', NATO, 4, 'us', 'The USSR cannot make Coup Attempts or Realignment rolls against any US controlled countries in Europe. US controlled countries in Europe cannot be attacked by play of the “#36 – Brush War” Event. This card requires prior play of either the “#16 – Warsaw Pact Formed” or “#23 – Marshall Plan” Event(s) in order to be played as an Event.', True),
                   Event('Independent Reds', Independent_Reds, 2, 'us', 'Add US Influence to either Yugoslavia, Romania, Bulgaria, Hungary, or Czechoslovakia so that it equals the USSR Influence in that country.', True),
                   Event('Marshall Plan', Marshall_Plan, 4, 'us', 'Add 1 US Influence to each of any 7 non-USSR controlled countries in Western Europe. This Event allows the “#21 – NATO” card to be played as an Event.', True),
                   Event('Indo-Pakistani War', Indo_Pakistani_War, 2, 'neutral', 'India invades Pakistan or vice versa (player’s choice). Roll a die and subtract (-1) from the die roll for every enemy controlled country adjacent to the target of the invasion (India or Pakistan). On a modified die roll of 4-6, the player receives 2 VP and replaces all the opponent’s Influence in the target country with their Influence. The player adds 2 to its Military Operations Track.'),
                   Event('Containment', Containment, 3, 'us', 'All Operations cards played by the US, for the remainder of this turn, receive +1 to their Operations value (to a maximum of 4 Operations per card).', True),
                   Event('CIA Created', CIA_Created, 1, 'us', 'The USSR reveals their hand of cards for this turn. The US may use the Operations value of this card to conduct Operations.', True),
                   Event('US/Japan Mutual Defense Pact', US_Japan_Mutual, 4, 'us', 'The US adds sufficient Influence to Japan for Control. The USSR cannot make Coup Attempts or Realignment rolls against Japan.', True),
                   Event('Suez Crisis', Suez_Crisis, 3, 'ussr', 'Remove a total of 4 US Influence from France, the United Kingdom and Israel (removing no more than 2 Influence per country).', True),
                   Event('East European Unrest', East_European_Unrest, 3, 'us', 'Early or Mid War: Remove 1 USSR Influence from 3 countries in Eastern Europe. Late War: Remove 2 USSR Influence from 3 countries in Eastern Europe.'),
                   Event('Decolonization', Decolonization, 3, 'ussr', 'Add 1 USSR Influence to each of any 4 countries in Africa and/or Southeast Asia.'),
                   Event('Red Scare/Purge', Red_Scare_Purge, 4, 'neutral', 'All Operations cards played by the opponent, for the remainder of this turn, receive -1 to their Operations value (to a minimum value of 1 Operations point).'),
                   Event('UN Intervention', UN_Intervention, 1, 'neutral', 'Play this card simultaneously with a card containing an opponent’s associated Event. The opponent’s associated Event is canceled but you may use the Operations value of the opponent’s card to conduct Operations. This Event cannot be played during the Headline Phase.'),
                   Event('The Cambridge Five', The_Cambridge_Five, 2, 'ussr', 'The US reveals all scoring cards in their hand of cards. The USSR player may add 1 USSR Influence to a single Region named on one of the revealed scoring cards. This card can not be played as an Event during the Late War.'),
                   Event('Special Relationship', Special_Relationship, 2, 'us', 'Add 1 US Influence to a single country adjacent to the U.K. if the U.K. is US-controlled but NATO is not in effect. Add 2 US Influence to a single country in Western Europe, and the US gains 2 VP, if the U.K. is US-controlled and NATO is in effect.'),
                   Event('NORAD', NORAD, 3, 'us', 'Add 1 US Influence to a single country containing US Influence, at the end of each Action Round, if Canada is US-controlled and the DEFCON level moved to 2 during that Action Round. This Event is canceled by the “#42 – Quagmire” Event.'),
                   )

#print(EARLY_WAR_CARDS)


class PlayableEvent:

    def __init__(self, destination):
        '''Metaclass for event cards when they are played.

        Parameters
        ----------
        destination : Pile (???)
            Where this card goes after resolution. Most regular events
            go to the discard pile and most starred events go to the
            removed from game pile, but others will need to do something
            else, like Missile Envy.
        '''

        self.destination = CardDestination[destination]


    def choices(self):
        '''Choices made available during the resolution of this card.

        To be implemented by the subclass if any choices.'''

        return None


    def __repr__(self):

        return self.__name__


