'''Things only useful for testing.'''

def basic_starting_influence(map):
	'''Basic strategy for starting influence. 

	US player adds 7 in Western Europe and 2 anywhere they have influence.
	USSR adds 6 in Eastern Europe.

	Until I implement proper setup choices for the AI, it's nice to have a 
	canonical setup for other testing.'''

	map.countries['West Germany'].us_influence += 4
	map.countries['Italy'].us_influence += 3
	map.countries['Iran'].us_influence += 2

	map.countries['East Germany'].ussr_influence += 1
	map.countries['Poland'].ussr_influence += 4
	map.countries['Yugoslavia'].ussr_influence += 1