import numpy as np
from CardGame import Card


"""
Functions for playing strategy
"""
def playing(player, deck):
    """
    Wrap-around min-max strategy
    """
    if not player.hand:
        return None

    # Represent original player hand as a boolean array
    my_hand = np.zeros(DECK_SIZE, dtype=bool)
    for my_card in player.hand + player.played_cards:
        card_idx = convert_card_to_index(my_card)
        my_hand[card_idx] = True

    # Reorder player's initial deck based on largest gap between adjacent cards
    reordered_indices = reorder_player_cards(my_hand)
    # print(f'reordered_indices: {reordered_indices}')
    
    # Play min_index card in odd rounds and max_index card in even rounds
    round = len(player.played_cards) + 1
    is_max = round % 2 == 0
    return play_next_available_card(player, reordered_indices, is_max)
            

def reorder_player_cards(my_hand):
    """
    Reorder player's initial deck based on largest gap between adjacent cards
    """
    # Find largest gap between adjacent cards and update min_index.
    # NOTE: min_index is the higher end of the gap (i.e., wrap-around).
    my_hand_indices = np.where(my_hand)[0]
    max_gap = 0
    min_index = None
    for i in range(OPENING_HAND_SIZE - 1):
        gap = my_hand_indices[i+1] - my_hand_indices[i]
        if gap > max_gap:
            max_gap = gap
            min_index = my_hand_indices[i+1]
    
    # Check wrap-around gap
    wrap_around_gap = my_hand_indices[0] + DECK_SIZE - my_hand_indices[-1]
    if wrap_around_gap > max_gap:
        max_gap = wrap_around_gap
        min_index = my_hand_indices[0]

    # Reorder deck based on min_index
    start_idx = np.where(my_hand_indices == min_index)[0][0]
    reordered_indices = np.concatenate((my_hand_indices[start_idx:], my_hand_indices[:start_idx]))
    return reordered_indices


def play_next_available_card(player, reordered_indices, is_max):
    """
    Play next available min or max card in hand
    """
    indices = reordered_indices[::-1] if is_max else reordered_indices
    for idx in indices:
        card = convert_index_to_card(idx)
        if card in player.hand:
            return player.hand.index(card)


"""
Functions for guessing strategy
"""
def guessing(player, cards, round):
    """
    Update available guesses and probabilities and return the top guesses by probability
    """
    # Initialize available guesses and probabilities
    available_guesses = np.ones(DECK_SIZE, dtype=bool)
    probabilities = np.full(DECK_SIZE, PAR_PROBABILITY, dtype=float)

    # Set wrap-around min/max based on partner's exposed cards
    min_idx, max_idx = set_min_max(player, round)

    # Update available guesses and probabilities
    update_available_guesses(player, available_guesses, min_idx, max_idx)
    update_probabilities(player, round, available_guesses, probabilities)

    # Return top guesses by probability
    candidate_guesses = get_candidate_guesses(round, probabilities, use_argmax=True)
    guesses = [card for card in cards if convert_card_to_index(card) in candidate_guesses]
    
    # DEBUG
    print(f'probabilities: {probabilities}')
    guess_indices = [convert_card_to_index(card) for card in guesses]
    print(f'guesses: {guess_indices}, cVals: {player.cVals}')

    return guesses


def set_min_max(player, round):
    """
    Set wrap-around min/max based on partner's exposed cards
    """
    partner_name = partner[player.name]
    if round % 2 == 1:
        min_card = player.exposed_cards[partner_name][-1]
        max_card = player.exposed_cards[partner_name][-2] if round > 1 else None
    else:
        max_card = player.exposed_cards[partner_name][-1]
        min_card = player.exposed_cards[partner_name][-2]

    min_idx = convert_card_to_index(min_card)
    max_idx = convert_card_to_index(max_card) if max_card else (min_idx - 4) % DECK_SIZE
    return min_idx, max_idx


def update_available_guesses(player, available_guesses, min_idx, max_idx):
    """
    Update available guesses by removing cards in hand, played and exposed cards,
    as well as cards outside of partner's min/max
    """
    for my_card in player.hand:
        card_idx = convert_card_to_index(my_card)
        available_guesses[card_idx] = False

    for played_card in player.played_cards:
        card_idx = convert_card_to_index(played_card)
        available_guesses[card_idx] = False

    for exposed_card_lst in player.exposed_cards.values():
        for exposed_card in exposed_card_lst:
            card_idx = convert_card_to_index(exposed_card)
            available_guesses[card_idx] = False

    # Remove cards outside of partner's min/max
    for i in range(max_idx + 1, min_idx):
        available_guesses[i % DECK_SIZE] = False


def update_probabilities(player, round, available_guesses, probabilities):
    """
    Update probabilities by various strategies
    """
    # Set unavailable cards to zero probability
    probabilities[~available_guesses] = 0

    # Update probabilities based on previous rounds' guesses and cVals
    partner_name = partner[player.name]
    opponents_names = opponents[player.name]

    for i in range(round - 1):
        # Compute accuracy based on cVals and exposed cards
        numerator = player.cVals[i]
        denominator = OPENING_HAND_SIZE - 1 - i
        for card in player.guesses[i]:
            # Decrement numerator and denominator if partner card is exposed
            if card in player.exposed_cards[partner_name]:
                numerator -= 1
                denominator -= 1
            # Decrement denominator if opponent card is exposed
            if card in player.exposed_cards[opponents_names[0]] or \
                card in player.exposed_cards[opponents_names[1]]:
                denominator -= 1
        accuracy = numerator / denominator if denominator > 0 else 0

        # Update probabilities based on accuracy
        for card in player.guesses[i]:
            card_idx = convert_card_to_index(card)
            if available_guesses[card_idx] and probabilities[card_idx] > 0 and probabilities[card_idx] < 1:
                probabilities[card_idx] = accuracy


def get_candidate_guesses(round, probabilities, use_argmax=True):
    """
    Get candidate guesses by max probability (argmax) or multinomial sampling (multinomial)
    """
    # Return top guesses by probability
    if use_argmax:
        return probabilities.argsort()[::-1][:13-round]

    # Return empty list if all probabilities are zero (error check for random.choice)
    if np.sum(probabilities) == 0:
        return []
    
    # Multinomial sampling
    normalized = probabilities / np.sum(probabilities)
    return np.random.choice(DECK_SIZE, 13-round, replace=False, p=normalized)


"""
Helper functions
"""
def convert_card_to_index(card):
    """
    Convert Card object to an index ranking by value then suit
    """
    suit_idx = suit_to_idx[card.suit]
    value_idx = value_to_idx[card.value]
    return value_idx * 4 + suit_idx


def convert_index_to_card(index):
    """
    Convert index to Card object
    """
    suit_idx = index % 4
    value_idx = index // 4
    suit = list(suit_to_idx.keys())[suit_idx]
    value = list(value_to_idx.keys())[value_idx]
    return Card(suit, value)


"""
Static global variables
"""
DECK_SIZE = 52
OPENING_HAND_SIZE = 13
PAR_PROBABILITY = 1/3

suit_to_idx = {"Diamonds": 0, "Clubs": 1, "Hearts": 2, "Spades": 3}
value_to_idx = {
    "2": 0,
    "3": 1,
    "4": 2,
    "5": 3,
    "6": 4,
    "7": 5,
    "8": 6,
    "9": 7,
    "10": 8,
    "J": 9,
    "Q": 10,
    "K": 11,
    "A": 12,
}
partner = {"North": "South", "East": "West", "South": "North", "West": "East"}
opponents = {
    "North": ["East", "West"],
    "East": ["South", "North"],
    "South": ["West", "East"],
    "West": ["North", "South"]
}
