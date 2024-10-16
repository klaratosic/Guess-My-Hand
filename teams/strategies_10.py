import numpy as np
from CardGame import Card


Debug = False

def DPrint(*args, **kwargs):
    if Debug:
        print(*args, **kwargs)

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
    # reordered_indices = np.where(my_hand)[0]
    DPrint(f'reordered indices: {reordered_indices}\n')
    
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
    for i in range(NUM_ROUNDS - 1):
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
    
    DPrint(f'probabilities: {probabilities}')
    DPrint(f'guesses: {[convert_card_to_index(card) for card in guesses]}, cVals: {player.cVals}')

    return guesses


def set_min_max(player, round):
    """
    Set wrap-around min/max based on partner's exposed cards
    """
    partner_name = partner[player.name]
    if round % 2 == 1:
        min_card = player.exposed_cards[partner_name][-1]
        max_card = player.exposed_cards[partner_name][-2] if round > 1 else None
        # max_card = player.exposed_cards[partner_name][-2] if round > 1 else convert_index_to_card(DECK_SIZE - 1)
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
    if max_idx < min_idx:
        for i in range(max_idx + 1, min_idx):
            available_guesses[i % DECK_SIZE] = False
    else:
        for i in range(max_idx + 1, DECK_SIZE):
            available_guesses[i] = False
        for i in range(min_idx):
            available_guesses[i] = False


def update_probabilities(player, round, available_guesses, probabilities):
    """
    Update probabilities by various strategies
    """
    DPrint(f'\nplayer: {player.name}\n')
    probabilities[~available_guesses] = 0
    partner_name = partner[player.name]
    adj_numerators = np.zeros(NUM_ROUNDS - 1, dtype=int)
    adj_denominators = np.zeros(NUM_ROUNDS - 1, dtype=int)

    # Compute accuracy per round (starting in round 2) based on cVals and exposed cards
    for i in range(round - 1):
        DPrint(f'round: {i+1}, available guesses: {np.where(available_guesses)}\n')
        numerator = player.cVals[i]
        denominator = NUM_ROUNDS - 1 - i
        curr_guesses = [convert_card_to_index(card) for card in player.guesses[i]]
        new_guesses = []
        new_numerator = 0
        new_denominator = 0
        DPrint(f'PRE: curr guesses: {curr_guesses}, numerator: {numerator}, denominator: {denominator}')

        if i >= 1:
            # Calculate accuracy of new guesses by backing up repeated previous guesses
            prev_guesses = [convert_card_to_index(card) for card in player.guesses[i-1]]
            new_guesses = list(set(curr_guesses) - set(prev_guesses))
            DPrint(f'prev guesses: {prev_guesses}, new guesses: {new_guesses}')

            # Process new guesses only if there are repeated previous guesses
            if len(new_guesses) != len(curr_guesses) and len(new_guesses) > 0:
                new_numerator = max(numerator - adj_numerators[i-1], 0)
                new_denominator = len(new_guesses)
                DPrint(f'new numerator: {new_numerator}, new denominator: {new_denominator}')
                for guess in new_guesses:
                    # Decrement denominator if card is not available (including partner card)
                    if guess in np.where(~available_guesses)[0]:
                        new_denominator -= 1
                        denominator -= 1
                    # Decrement numerator if partner card is exposed
                    if convert_index_to_card(guess) in player.exposed_cards[partner_name]:
                        new_numerator -= 1
                        numerator -= 1
                new_accuracy = new_numerator / new_denominator if new_denominator > 0 else 0
                # Update probabilities based on new accuracy if still available
                for guess in new_guesses:
                    if available_guesses[guess] and probabilities[guess] > 0 and probabilities[guess] < 1:
                        probabilities[guess] = new_accuracy

        DPrint(f'new numerator: {new_numerator}, new denominator: {new_denominator}')

        # Update probabilities of old guesses or all new guesses if no repeated previous guesses
        old_guesses = [guess for guess in curr_guesses if guess not in new_guesses]
        guesses = old_guesses if old_guesses else curr_guesses
        DPrint(f'old guesses: {old_guesses}, guesses: {guesses}')
        for guess in guesses:
            # Decrement denominator if card is not available (including partner card)
            if guess in np.where(~available_guesses)[0]:
                denominator -= 1
            # Decrement numerator if partner card is exposed
            if convert_index_to_card(guess) in player.exposed_cards[partner_name]:
                numerator -= 1

        # Update adjusted numerators and denominators
        adj_numerators[i] = numerator
        adj_denominators[i] = denominator
        old_numerator = numerator - new_numerator
        old_denominator = denominator - new_denominator
        accuracy = old_numerator / old_denominator if old_denominator > 0 else 0
        DPrint(f'POST: numerator: {numerator}, denominator: {denominator}, accuracy: {accuracy}\n')
        
        for guess in guesses:
            if available_guesses[guess] and probabilities[guess] > 0 and probabilities[guess] < 1:
                probabilities[guess] = accuracy


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
NUM_ROUNDS = 13
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
