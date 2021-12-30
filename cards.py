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

    # TODO: add NORAD trigger
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


@check_game_end
def Brush_War(gamestate):
    '''The player attacks any country with a stability number of 1 or 2. 
    Roll a die and subtract (-1) from the die roll for every adjacent enemy controlled 
    country. On a modified die roll of 3-6, the player receives 1 VP and replaces all 
    the opponent’s Influence in the target country with their Influence. The player 
    adds 3 to its Military Operations Track.'''

    pass


@check_game_end
def Arms_Race(gamestate):
    '''Compare each player’s value on the Military Operations Track. If the phasing 
    player has a higher value than their opponent on the Military Operations Track, 
    that player receives 1 VP. If the phasing player has a higher value than their 
    opponent, and has met the “required” amount, on the Military Operations Track, 
    that player receives 3 VP instead.'''

    pass


@check_game_end
def Cuban_Missile_Crisis(gamestate):
    '''Set the DEFCON level to 2. Any Coup Attempts by your opponent, for the remainder 
    of this turn, will result in Global Thermonuclear War. Your opponent will lose the game. 
    This card’s Event may be canceled, at any time, if the USSR removes 2 Influence from 
    Cuba or the US removes 2 Influence from West Germany or Turkey.'''

    pass


@check_game_end
def Nuclear_Subs(gamestate):
    '''US Operations used for Coup Attempts in Battleground countries, for the remainder 
    of this turn, do not degrade the DEFCON level. This card’s Event does not apply to 
    any Event that would affect the DEFCON level (ex. the “#40 – Cuban Missile Crisis” Event).
    '''

    pass


@check_game_end
def Quagmire(gamestate):
    '''On the US’s next action round, it must discard an Operations card with a value of 2 
    or more and roll 1-4 on a die to cancel this Event. Repeat this Event for each US action 
    round until the US successfully rolls 1-4 on a die. If the US is unable to discard an 
    Operations card, it must play all of its scoring cards and then skip each action round 
    for the rest of the turn. This Event cancels the effect(s) of the “#106 – NORAD” Event 
    (if applicable).'''

    pass


@check_game_end
def SALT_Negotiations(gamestate):
    '''Improve the DEFCON level by 2. For the remainder of the turn, both players receive -1 
    to all Coup Attempt rolls. The player of this card’s Event may look through the discard 
    pile, pick any 1 non-scoring card, reveal it to their opponent and then place the drawn 
    card into their hand.'''

    pass


@check_game_end
def Bear_Trap(gamestate):
    '''On the USSR’s next action round, it must discard an Operations card with a value of 2 
    or more and roll 1-4 on a die to cancel this Event. Repeat this Event for each USSR action 
    round until the USSR successfully rolls 1-4 on a die. If the USSR is unable to discard an 
    Operations card, it must play all of its scoring cards and then skip each action round for 
    the rest of the turn.'''

    pass


@check_game_end
def Summit(gamestate):
    '''Both players roll a die. Each player receives +1 to the die roll for each Region 
    (Europe, Asia, etc.) they Dominate or Control. The player with the highest modified die 
    roll receives 2 VP and may degrade or improve the DEFCON level by 1 (do not reroll ties).
    '''

    pass


@check_game_end
def How_I_Learned(gamestate):
    '''Set the DEFCON level to any level desired (1-5). The player adds 5 to its Military 
    Operations Track.
    '''

    pass


@check_game_end
def Junta(gamestate):
    '''Add 2 Influence to a single country in Central or South America. The player may 
    make free Coup Attempts or Realignment rolls in either Central or South America using 
    the Operations value of this card.'''

    pass


@check_game_end
def Kitchen_Debates(gamestate):
    '''If the US controls more Battleground countries than the USSR, the US player uses this 
    Event to poke their opponent in the chest and receive 2 VP!'''

    pass


@check_game_end
def Missile_Envy(gamestate):
    '''Exchange this card for your opponent’s highest value Operations card. If 2 or more 
    cards are tied, opponent chooses. If the exchanged card contains an Event applicable to 
    yourself or both players, it occurs immediately. If it contains an opponent’s Event, 
    use the Operations value (no Event). The opponent must use this card for Operations 
    during their next action round.'''

    pass


@check_game_end
def We_Will_Bury_You(gamestate):
    '''Degrade the DEFCON level by 1. Unless the #32 UN Intervention card is played as an 
    Event on the US’s next action round, the USSR receives 3 VP.
    '''

    pass


@check_game_end
def Brezhnev_Doctrine(gamestate):
    '''All Operations cards played by the USSR, for the remainder of this turn, receive +1 
    to their Operations value (to a maximum of 4 Operations per card).
    '''

    pass


@check_game_end
def Portuguese_Empire_Crumbles(gamestate):
    '''Add 2 USSR Influence to Angola and the SE African States.'''

    pass


@check_game_end
def South_African_Unrest(gamestate):
    '''The USSR either adds 2 Influence to South Africa or adds 1 Influence to South Africa 
    and 2 Influence to a single country adjacent to South Africa.'''

    pass


@check_game_end
def Allende(gamestate):
    '''Add 2 USSR Influence to Chile.'''

    pass


@check_game_end
def Willy_Brandt(gamestate):
    '''The USSR receives 1 VP and adds 1 Influence to West Germany. This Event cancels the 
    effect(s) of the “#21 – NATO” Event for West Germany only. This Event is prevented / 
    canceled by the “#96 – Tear Down this Wall” Event.'''

    pass


@check_game_end
def Muslim_Revolution(gamestate):
    '''Remove all US Influence from 2 of the following countries: Sudan, Iran, Iraq, 
    Egypt, Libya, Saudi Arabia, Syria, Jordan. This Event cannot be used after the 
    “#110 – AWACS Sale to Saudis” Event has been played.'''

    pass


@check_game_end
def ABM_Treaty(gamestate):
    '''Improve the DEFCON level by 1 and then conduct Operations using the Operations 
    value of this card.'''

    pass


@check_game_end
def Cultural_Revolution(gamestate):
    '''If the US has the “#6 – The China Card” card, the US must give the card to the 
    USSR (face up and available to be played). If the USSR already has “#6 – The China Card” 
    card, the USSR receives 1 VP.'''

    pass


@check_game_end
def Flower_Power(gamestate):
    '''The USSR receives 2 VP for every US played “War” card (Arab-Israeli War, Korean War, 
    Brush War, Indo-Pakistani War, Iran-Iraq War), used for Operations or an Event, after 
    this card is played. This Event is prevented / canceled by the “#97 – ‘An Evil Empire’” 
    Event.'''

    pass


@check_game_end
def U2_Incident(gamestate):
    '''The USSR receives 1 VP. If the “#32 – UN Intervention” Event is played later this 
    turn, either by the US or the USSR, the USSR receives an additional 1 VP.
    '''

    pass


@check_game_end
def OPEC(gamestate):
    '''The USSR receives 1 VP for Control of each of the following countries: Egypt, Iran, 
    Libya, Saudi Arabia, Iraq, Gulf States, Venezuela. This Event cannot be used after the 
    “#86 – North Sea Oil” Event has been played.
    '''

    pass


@check_game_end
def Lone_Gunman(gamestate):
    '''The US reveals their hand of cards. The USSR may use the Operations value of this 
    card to conduct Operations.
    '''

    pass


@check_game_end
def Colonial_Rear_Guards(gamestate):
    '''Add 1 US Influence to each of any 4 countries in Africa and/or Southeast Asia.
    '''

    pass


@check_game_end
def Panama_Canal_Returned(gamestate):
    '''Add 1 US Influence to Panama, Costa Rica and Venezuela.
    '''

    pass


@check_game_end
def Camp_David_Accords(gamestate):
    '''The US receives 1 VP and adds 1 Influence to Israel, Jordan and Egypt. This Event 
    prevents the “#13 – Arab-Israeli War” card from being played as an Event.
    '''

    pass


@check_game_end
def Puppet_Governments(gamestate):
    '''The US may add 1 Influence to 3 countries that do not contain Influence from either 
    the US or USSR.
    '''

    pass


@check_game_end
def Grain_Sales_to_Soviets(gamestate):
    '''The US randomly selects 1 card from the USSR’s hand (if available). The US must 
    either play the card or return it to the USSR. If the card is returned, or the USSR 
    has no cards, the US may use the Operations value of this card to conduct Operations.
    '''

    pass


@check_game_end
def John_Paul_II(gamestate):
    '''Remove 2 USSR Influence from Poland and add 1 US Influence to Poland. This Event 
    allows the “#101 – Solidarity” card to be played as an Event.
    '''

    pass


@check_game_end
def Latin_American_Death_Squads(gamestate):
    '''All of the phasing player’s Coup Attempts in Central and South America, for the 
    remainder of this turn, receive +1 to their die roll. All of the opponent’s Coup 
    Attempts in Central and South America, for the remainder of this turn, receive -1 
    to their die roll.
    '''

    pass


@check_game_end
def OAS_Founded(gamestate):
    '''Add a total of 2 US Influence to any countries in Central or South America.
    '''

    pass


@check_game_end
def Nixon_Plays(gamestate):
    '''If the USSR has the “#6 – The China Card” card, the USSR must give the card to 
    the US (face down and unavailable for immediate play). If the US already has the 
    “#6 – The China Card” card, the US receives 2 VP.
    '''

    pass


@check_game_end
def Sadat_Expels_Soviets(gamestate):
    '''Remove all USSR Influence from Egypt and add 1 US Influence to Egypt.
    '''

    pass


@check_game_end
def Shuttle_Diplomacy(gamestate):
    '''If this card’s Event is in effect, subtract (-1) a Battleground country from the 
    USSR total and then discard this card during the next scoring of the Middle East or 
    Asia (which ever comes first).
    '''

    pass


@check_game_end
def VOA(gamestate):
    '''Remove 4 USSR Influence from any countries NOT in Europe (removing no more than 2 
    Influence per country).
    '''

    pass


@check_game_end
def Liberation_Theology(gamestate):
    '''Add a total of 3 USSR Influence to any countries in Central America (adding no more 
    than 2 Influence per country).
    '''

    pass


@check_game_end
def Ussuri_River_Skirmish(gamestate):
    '''If the USSR has the “#6 – The China Card” card, the USSR must give the card to the 
    US (face up and available for play). If the US already has the “#6 – The China Card” 
    card, add a total of 4 US Influence to any countries in Asia (adding no more than 2 
    Influence per country).
    '''

    pass


@check_game_end
def Ask_Not(gamestate):
    '''The US may discard up to their entire hand of cards (including scoring cards) to 
    the discard pile and draw replacements from the draw pile. The number of cards to be 
    discarded must be decided before drawing any replacement cards from the draw pile.
    '''

    pass


@check_game_end
def Alliance_for_Progress(gamestate):
    '''The US receives 1 VP for each US controlled Battleground country in Central and 
    South America.
    '''

    pass


@check_game_end
def One_Small_Step(gamestate):
    '''If you are behind on the Space Race Track, the player uses this Event to move their 
    marker 2 spaces forward on the Space Race Track. The player receives VP only from the 
    final space moved into.
    '''

    pass


@check_game_end
def Che(gamestate):
    '''The USSR may perform a Coup Attempt, using this card’s Operations value, against a 
    non-Battleground country in Central America, South America or Africa. The USSR may 
    perform a second Coup Attempt, against a different non-Battleground country in Central 
    America, South America or Africa, if the first Coup Attempt removed any US Influence 
    from the target country.
    '''

    pass


@check_game_end
def Our_Man_in_Tehran(gamestate):
    '''If the US controls at least one Middle East country, the US player uses this Event 
    to draw the top 5 cards from the draw pile. The US may discard any or all of the drawn 
    cards, after revealing the discarded card(s) to the USSR player, without triggering 
    the Event(s). Any remaining drawn cards are returned to the draw pile and the draw 
    pile is reshuffled.
    '''

    pass



MID_WAR_CARDS = (Event('Brush War', Brush_War, 3, 'neutral', 'The player attacks any country with a stability number of 1 or 2. Roll a die and subtract (-1) from the die roll for every adjacent enemy controlled country. On a modified die roll of 3-6, the player receives 1 VP and replaces all the opponent’s Influence in the target country with their Influence. The player adds 3 to its Military Operations Track.'),
                 ScoringCard('central_am'),
                 ScoringCard('southeast_asia'),
                 Event('Arms Race', Arms_Race, 3, 'neutral', 'Compare each player’s value on the Military Operations Track. If the phasing player has a higher value than their opponent on the Military Operations Track, that player receives 1 VP. If the phasing player has a higher value than their opponent, and has met the “required” amount, on the Military Operations Track, that player receives 3 VP instead.'),
                 Event('Cuban Missile Crisis', Cuban_Missile_Crisis, 3, 'neutral', 'Set the DEFCON level to 2. Any Coup Attempts by your opponent, for the remainder of this turn, will result in Global Thermonuclear War. Your opponent will lose the game. This card’s Event may be canceled, at any time, if the USSR removes 2 Influence from Cuba or the US removes 2 Influence from West Germany or Turkey.', True),
                 Event('Nuclear Subs', Nuclear_Subs, 2, 'us', 'US Operations used for Coup Attempts in Battleground countries, for the remainder of this turn, do not degrade the DEFCON level. This card’s Event does not apply to any Event that would affect the DEFCON level (ex. the “#40 – Cuban Missile Crisis” Event).', True),
                 Event('Quagmire', Quagmire, 3, 'ussr', 'On the US’s next action round, it must discard an Operations card with a value of 2 or more and roll 1-4 on a die to cancel this Event. Repeat this Event for each US action round until the US successfully rolls 1-4 on a die. If the US is unable to discard an Operations card, it must play all of its scoring cards and then skip each action round for the rest of the turn. This Event cancels the effect(s) of the “#106 – NORAD” Event (if applicable).', True),
                 Event('SALT Negotiations', SALT_Negotiations, 3, 'neutral', 'Improve the DEFCON level by 2. For the remainder of the turn, both players receive -1 to all Coup Attempt rolls. The player of this card’s Event may look through the discard pile, pick any 1 non-scoring card, reveal it to their opponent and then place the drawn card into their hand.', True),
                 Event('Bear Trap', Bear_Trap, 3, 'us', 'On the USSR’s next action round, it must discard an Operations card with a value of 2 or more and roll 1-4 on a die to cancel this Event. Repeat this Event for each USSR action round until the USSR successfully rolls 1-4 on a die. If the USSR is unable to discard an Operations card, it must play all of its scoring cards and then skip each action round for the rest of the turn.', True),
                 Event('Summit', Summit, 1, 'neutral', 'Both players roll a die. Each player receives +1 to the die roll for each Region (Europe, Asia, etc.) they Dominate or Control. The player with the highest modified die roll receives 2 VP and may degrade or improve the DEFCON level by 1 (do not reroll ties).'),
                 Event('How I Learned to Stop Worrying', How_I_Learned, 2, 'neutral', 'Set the DEFCON level to any level desired (1-5). The player adds 5 to its Military Operations Track.', True),
                 Event('Junta', Junta, 2, 'neutral', 'Add 2 Influence to a single country in Central or South America. The player may make free Coup Attempts or Realignment rolls in either Central or South America using the Operations value of this card.'),
                 Event('Kitchen Debates', Kitchen_Debates, 1, 'us', 'If the US controls more Battleground countries than the USSR, the US player uses this Event to poke their opponent in the chest and receive 2 VP!', True),
                 Event('Missile Envy', Missile_Envy, 2, 'neutral', 'Exchange this card for your opponent’s highest value Operations card. If 2 or more cards are tied, opponent chooses. If the exchanged card contains an Event applicable to yourself or both players, it occurs immediately. If it contains an opponent’s Event, use the Operations value (no Event). The opponent must use this card for Operations during their next action round.'),
                 Event('We Will Bury You', We_Will_Bury_You, 4, 'ussr', 'Degrade the DEFCON level by 1. Unless the #32 UN Intervention card is played as an Event on the US’s next action round, the USSR receives 3 VP.', True),
                 Event('Brezhnev Doctrine', Brezhnev_Doctrine, 3, 'ussr', 'All Operations cards played by the USSR, for the remainder of this turn, receive +1 to their Operations value (to a maximum of 4 Operations per card).', True),
                 Event('Portuguese Empire Crumbles', Portuguese_Empire_Crumbles, 2, 'ussr', 'Add 2 USSR Influence to Angola and the SE African States.', True),
                 Event('South African Unrest', South_African_Unrest, 2, 'ussr', 'The USSR either adds 2 Influence to South Africa or adds 1 Influence to South Africa and 2 Influence to a single country adjacent to South Africa.'),
                 Event('Allende', Allende, 1, 'ussr', 'Add 2 USSR Influence to Chile.', True),
                 Event('Willy Brandt', Willy_Brandt, 2, 'ussr', 'The USSR receives 1 VP and adds 1 Influence to West Germany. This Event cancels the effect(s) of the “#21 – NATO” Event for West Germany only. This Event is prevented / canceled by the “#96 – Tear Down this Wall” Event.', True),
                 Event('Muslim Revolution', Muslim_Revolution, 4, 'ussr', 'Remove all US Influence from 2 of the following countries: Sudan, Iran, Iraq, Egypt, Libya, Saudi Arabia, Syria, Jordan. This Event cannot be used after the “#110 – AWACS Sale to Saudis” Event has been played.'),
                 Event('ABM Treaty', ABM_Treaty, 4, 'neutral', 'Improve the DEFCON level by 1 and then conduct Operations using the Operations value of this card.'),
                 Event('Cultural Revolution', Cultural_Revolution, 3, 'ussr', 'If the US has the “#6 – The China Card” card, the US must give the card to the USSR (face up and available to be played). If the USSR already has “#6 – The China Card” card, the USSR receives 1 VP.', True),
                 Event('Flower Power', Flower_Power, 4, 'ussr', 'The USSR receives 2 VP for every US played “War” card (Arab-Israeli War, Korean War, Brush War, Indo-Pakistani War, Iran-Iraq War), used for Operations or an Event, after this card is played. This Event is prevented / canceled by the “#97 – ‘An Evil Empire’” Event.', True),
                 Event('U2 Incident', U2_Incident, 3, 'ussr', 'The USSR receives 1 VP. If the “#32 – UN Intervention” Event is played later this turn, either by the US or the USSR, the USSR receives an additional 1 VP.', True),
                 Event('OPEC', OPEC, 3, 'ussr', 'The USSR receives 1 VP for Control of each of the following countries: Egypt, Iran, Libya, Saudi Arabia, Iraq, Gulf States, Venezuela. This Event cannot be used after the “#86 – North Sea Oil” Event has been played.'),
                 Event('"Lone Gunman"', Lone_Gunman, 1, 'ussr', 'The US reveals their hand of cards. The USSR may use the Operations value of this card to conduct Operations.', True),
                 Event('Colonial Rear Guards', Colonial_Rear_Guards, 2, 'us', 'Add 1 US Influence to each of any 4 countries in Africa and/or Southeast Asia.'),
                 Event('Panama Canal Returned', Panama_Canal_Returned, 1, 'us', 'Add 1 US Influence to Panama, Costa Rica and Venezuela.', True),
                 Event('Camp David Accords', Camp_David_Accords, 2, 'us', 'The US receives 1 VP and adds 1 Influence to Israel, Jordan and Egypt. This Event prevents the “#13 – Arab-Israeli War” card from being played as an Event.', True),
                 Event('Puppet Governments', Puppet_Governments, 2, 'us', 'The US may add 1 Influence to 3 countries that do not contain Influence from either the US or USSR.', True),
                 Event('Grain Sales to Soviets', Grain_Sales_to_Soviets, 2, 'us', 'The US randomly selects 1 card from the USSR’s hand (if available). The US must either play the card or return it to the USSR. If the card is returned, or the USSR has no cards, the US may use the Operations value of this card to conduct Operations.'),
                 Event('John Paul II Elected Pope', John_Paul_II, 2, 'us', 'Remove 2 USSR Influence from Poland and add 1 US Influence to Poland. This Event allows the “#101 – Solidarity” card to be played as an Event.', True),
                 Event('Latin American Death Squads', Latin_American_Death_Squads, 2, 'neutral', 'All of the phasing player’s Coup Attempts in Central and South America, for the remainder of this turn, receive +1 to their die roll. All of the opponent’s Coup Attempts in Central and South America, for the remainder of this turn, receive -1 to their die roll.'),
                 Event('OAS Founded', OAS_Founded, 1, 'us', 'Add a total of 2 US Influence to any countries in Central or South America.', True),
                 Event('Nixon Plays the China Card', Nixon_Plays, 2, 'us', 'If the USSR has the “#6 – The China Card” card, the USSR must give the card to the US (face down and unavailable for immediate play). If the US already has the “#6 – The China Card” card, the US receives 2 VP.', True),
                 Event('Sadat Expels Soviets', Sadat_Expels_Soviets, 1, 'us', 'Remove all USSR Influence from Egypt and add 1 US Influence to Egypt.', True),
                 Event('Shuttle Diplomacy', Shuttle_Diplomacy, 3, 'us', 'If this card’s Event is in effect, subtract (-1) a Battleground country from the USSR total and then discard this card during the next scoring of the Middle East or Asia (which ever comes first).'),
                 Event('The Voice of America', VOA, 2, 'us', 'Remove 4 USSR Influence from any countries NOT in Europe (removing no more than 2 Influence per country).'),
                 Event('Liberation Theology', Liberation_Theology, 2, 'ussr', 'Add a total of 3 USSR Influence to any countries in Central America (adding no more than 2 Influence per country).'),
                 Event('Ussuri River Skirmish', Ussuri_River_Skirmish, 3, 'us', 'If the USSR has the “#6 – The China Card” card, the USSR must give the card to the US (face up and available for play). If the US already has the “#6 – The China Card” card, add a total of 4 US Influence to any countries in Asia (adding no more than 2 Influence per country).', True),
                 Event('Ask Not What Your Country...', Ask_Not, 3, 'us', 'The US may discard up to their entire hand of cards (including scoring cards) to the discard pile and draw replacements from the draw pile. The number of cards to be discarded must be decided before drawing any replacement cards from the draw pile.', True),
                 Event('Alliance for Progress', Alliance_for_Progress, 3, 'us', 'The US receives 1 VP for each US controlled Battleground country in Central and South America.', True),
                 ScoringCard('africa'),
                 Event('"One Small Step..."', One_Small_Step, 2, 'neutral', 'If you are behind on the Space Race Track, the player uses this Event to move their marker 2 spaces forward on the Space Race Track. The player receives VP only from the final space moved into.'),
                 ScoringCard('south_am'),
                 Event('Che', Che, 3, 'ussr', 'The USSR may perform a Coup Attempt, using this card’s Operations value, against a non-Battleground country in Central America, South America or Africa. The USSR may perform a second Coup Attempt, against a different non-Battleground country in Central America, South America or Africa, if the first Coup Attempt removed any US Influence from the target country.'),
                 Event('Our Man in Tehran', Our_Man_in_Tehran, 2, 'us', 'If the US controls at least one Middle East country, the US player uses this Event to draw the top 5 cards from the draw pile. The US may discard any or all of the drawn cards, after revealing the discarded card(s) to the USSR player, without triggering the Event(s). Any remaining drawn cards are returned to the draw pile and the draw pile is reshuffled.', True),
                 )

#print(EARLY_WAR_CARDS)


@check_game_end
def Iranian_Hostage_Crisis(gamestate):
    '''Remove all US Influence and add 2 USSR Influence to Iran. This card’s Event requires 
    the US to discard 2 cards, instead of 1 card, if the “#92 – Terrorism” Event is played.
    '''

    pass


@check_game_end
def The_Iron_Lady(gamestate):
    '''Add 1 USSR Influence to Argentina and remove all USSR Influence from the United 
    Kingdom. The US receives 1 VP. This Event prevents the “#7 – Socialist Governments” 
    card from being played as an Event.
    '''

    pass


@check_game_end
def Reagan_Bombs_Libya(gamestate):
    '''The US receives 1 VP for every 2 USSR Influence in Libya.
    '''

    pass


@check_game_end
def Star_Wars(gamestate):
    '''If the US is ahead on the Space Race Track, the US player uses this Event to look 
    through the discard pile, pick any 1 non-scoring card and play it immediately as an Event.
    '''

    pass


@check_game_end
def North_Sea_Oil(gamestate):
    '''The US may play 8 cards (in 8 action rounds) for this turn only. This Event 
    prevents the “#61 – OPEC” card from being played as an Event.
    '''

    pass


@check_game_end
def The_Reformer(gamestate):
    '''Add 4 USSR Influence to Europe (adding no more than 2 Influence per country). 
    If the USSR is ahead of the US in VP, 6 Influence may be added to Europe instead. 
    The USSR may no longer make Coup Attempts in Europe.
    '''

    pass


@check_game_end
def Marine_Barracks_Bombing(gamestate):
    '''Remove all US Influence in Lebanon and remove a total of 2 US Influence from 
    any countries in the Middle East.
    '''

    pass


@check_game_end
def Soviets_Shoot_Down(gamestate):
    '''Degrade the DEFCON level by 1 and the US receives 2 VP. The US may place influence 
    or make Realignment rolls, using this card, if South Korea is US controlled.
    '''

    pass


@check_game_end
def Glasnost(gamestate):
    '''Improve the DEFCON level by 1 and the USSR receives 2 VP. The USSR may make 
    Realignment rolls or add Influence, using this card, if the “#87 – The Reformer” 
    Event has already been played.
    '''

    pass


@check_game_end
def Ortega_Elected(gamestate):
    '''Remove all US Influence from Nicaragua. The USSR may make a free Coup Attempt, 
    using this card’s Operations value, in a country adjacent to Nicaragua.
    '''

    pass


@check_game_end
def Terrorism(gamestate):
    '''The player’s opponent must randomly discard 1 card from their hand. If the 
    “#82 – Iranian Hostage Crisis” Event has already been played, a US player 
    (if applicable) must randomly discard 2 cards from their hand.
    '''

    pass


@check_game_end
def Iran_Contra_Scandal(gamestate):
    '''All US Realignment rolls, for the remainder of this turn, receive -1 to their die roll.
    '''

    pass


@check_game_end
def Chernobyl(gamestate):
    '''The US must designate a single Region (Europe, Asia, etc.) that, for the remainder of 
    the turn, the USSR cannot add Influence to using Operations points.
    '''

    pass


@check_game_end
def Latin_American_Debt_Crisis(gamestate):
    '''The US must immediately discard a card with an Operations value of 3 or more or the 
    USSR may double the amount of USSR Influence in 2 countries in South America.
    '''

    pass


@check_game_end
def Tear_Down_this_Wall(gamestate):
    '''Add 3 US Influence to East Germany. The US may make free Coup Attempts or Realignment 
    rolls in Europe using the Operations value of this card. This Event prevents / cancels 
    the effect(s) of the “#55 – Willy Brandt” Event.
    '''

    pass


@check_game_end
def An_Evil_Empire(gamestate):
    '''The US receives 1 VP. This Event prevents / cancels the effect(s) of the 
    “#59 – Flower Power” Event.
    '''

    pass


@check_game_end
def Aldrich_Ames_Remix(gamestate):
    '''The US reveals their hand of cards, face-up, for the remainder of the turn and the USSR discards a card from the US hand.
    '''

    pass


@check_game_end
def Pershing_II_Deployed(gamestate):
    '''The USSR receives 1 VP. Remove 1 US Influence from any 3 countries in Western Europe.
    '''

    pass


@check_game_end
def Wargames(gamestate):
    '''If the DEFCON level is 2, the player may immediately end the game after giving their 
    opponent 6 VP. How about a nice game of chess?
    '''

    pass


@check_game_end
def Solidarity(gamestate):
    '''Add 3 US Influence to Poland. This card requires prior play of the 
    “#68 – John Paul II Elected Pope” Event in order to be played as an Event.
    '''

    pass


@check_game_end
def Iran_Iraq_War(gamestate):
    '''Iran invades Iraq or vice versa (player’s choice). Roll a die and subtract (-1) 
    from the die roll for every enemy controlled country adjacent to the target of the 
    invasion (Iran or Iraq). On a modified die roll of 4-6, the player receives 2 VP 
    and replaces all the opponent’s Influence in the target country with their Influence. 
    The player adds 2 to its Military Operations Track.
    '''

    pass


@check_game_end
def Yuri_and_Samantha(gamestate):
    '''The USSR receives 1 VP for each US Coup Attempt performed during the remainder 
    of the Turn.
    '''

    pass


@check_game_end
def AWACS(gamestate):
    '''Add 2 US Influence to Saudi Arabia. This Event prevents the “#56 – Muslim Revolution” 
    card from being played as an Event.
    '''

    pass


LATE_WAR_CARDS = (Event('Iranian Hostage Crisis', Iranian_Hostage_Crisis, 3, 'ussr', 'Remove all US Influence and add 2 USSR Influence to Iran. This card’s Event requires the US to discard 2 cards, instead of 1 card, if the “#92 – Terrorism” Event is played.', True),
                  Event('The Iron Lady', The_Iron_Lady, 3, 'us', 'Add 1 USSR Influence to Argentina and remove all USSR Influence from the United Kingdom. The US receives 1 VP. This Event prevents the “#7 – Socialist Governments” card from being played as an Event.', True),
                  Event('Reagan Bombs Libya', Reagan_Bombs_Libya, 2, 'us', 'The US receives 1 VP for every 2 USSR Influence in Libya.', True),
                  Event('Star Wars', Star_Wars, 2, 'us', 'If the US is ahead on the Space Race Track, the US player uses this Event to look through the discard pile, pick any 1 non-scoring card and play it immediately as an Event.', True),
                  Event('North Sea Oil', North_Sea_Oil, 3, 'us', 'The US may play 8 cards (in 8 action rounds) for this turn only. This Event prevents the “#61 – OPEC” card from being played as an Event.', True),
                  Event('The Reformer', The_Reformer, 3, 'ussr', 'Add 4 USSR Influence to Europe (adding no more than 2 Influence per country). If the USSR is ahead of the US in VP, 6 Influence may be added to Europe instead. The USSR may no longer make Coup Attempts in Europe.', True),
                  Event('Marine Barracks Bombing', Marine_Barracks_Bombing, 2, 'ussr', 'Remove all US Influence in Lebanon and remove a total of 2 US Influence from any countries in the Middle East.', True),
                  Event('Soviets Shoot Down KAL-007', Soviets_Shoot_Down, 4, 'us', 'Degrade the DEFCON level by 1 and the US receives 2 VP. The US may place influence or make Realignment rolls, using this card, if South Korea is US controlled.', True),
                  Event('Glasnost', Glasnost, 4, 'ussr', 'Improve the DEFCON level by 1 and the USSR receives 2 VP. The USSR may make Realignment rolls or add Influence, using this card, if the “#87 – The Reformer” Event has already been played.', True),
                  Event('Ortega Elected in Nicaragua', Ortega_Elected, 2, 'ussr', 'Remove all US Influence from Nicaragua. The USSR may make a free Coup Attempt, using this card’s Operations value, in a country adjacent to Nicaragua.', True),
                  Event('Terrorism', Terrorism, 2, 'neutral', 'The player’s opponent must randomly discard 1 card from their hand. If the “#82 – Iranian Hostage Crisis” Event has already been played, a US player (if applicable) must randomly discard 2 cards from their hand.'),
                  Event('Iran-Contra Scandal', Iran_Contra_Scandal, 2, 'ussr', 'All US Realignment rolls, for the remainder of this turn, receive -1 to their die roll.', True),
                  Event('Chernobyl', Chernobyl, 3, 'us', 'The US must designate a single Region (Europe, Asia, etc.) that, for the remainder of the turn, the USSR cannot add Influence to using Operations points.', True),
                  Event('Latin American Debt Crisis', Latin_American_Debt_Crisis, 2, 'ussr', 'The US must immediately discard a card with an Operations value of 3 or more or the USSR may double the amount of USSR Influence in 2 countries in South America.'),
                  Event('Tear Down this Wall', Tear_Down_this_Wall, 3, 'us', 'Add 3 US Influence to East Germany. The US may make free Coup Attempts or Realignment rolls in Europe using the Operations value of this card. This Event prevents / cancels the effect(s) of the “#55 – Willy Brandt” Event.', True),
                  Event('"An Evil Empire"', An_Evil_Empire, 3, 'us', 'The US receives 1 VP. This Event prevents / cancels the effect(s) of the “#59 – Flower Power” Event.', True),
                  Event('Aldrich Ames Remix', Aldrich_Ames_Remix, 3, 'ussr', 'The US reveals their hand of cards, face-up, for the remainder of the turn and the USSR discards a card from the US hand.', True),
                  Event('Pershing II Deployed', Pershing_II_Deployed, 3, 'ussr', 'The USSR receives 1 VP. Remove 1 US Influence from any 3 countries in Western Europe.', True),
                  Event('Wargames', Wargames, 4, 'neutral', 'If the DEFCON level is 2, the player may immediately end the game after giving their opponent 6 VP. How about a nice game of chess?', True),
                  Event('Solidarity', Solidarity, 2, 'us', 'Add 3 US Influence to Poland. This card requires prior play of the “#68 – John Paul II Elected Pope” Event in order to be played as an Event.', True),
                  Event('Iran-Iraq War', Iran_Iraq_War, 2, 'neutral', 'Iran invades Iraq or vice versa (player’s choice). Roll a die and subtract (-1) from the die roll for every enemy controlled country adjacent to the target of the invasion (Iran or Iraq). On a modified die roll of 4-6, the player receives 2 VP and replaces all the opponent’s Influence in the target country with their Influence. The player adds 2 to its Military Operations Track.', True),
                  Event('Yuri and Samantha', Yuri_and_Samantha, 2, 'ussr', 'The USSR receives 1 VP for each US Coup Attempt performed during the remainder of the Turn.', True),
                  Event('AWACS Sale to Saudis', AWACS, 3, 'us', 'Add 2 US Influence to Saudi Arabia. This Event prevents the “#56 – Muslim Revolution” card from being played as an Event.', True),
                  )


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


