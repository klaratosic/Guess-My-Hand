import numpy as np
import random

# Shared global variables
PARTNERS = {
    "North": "South",
    "East": "West",
    "South": "North",
    "West": "East",
}
SUIT_ORDER = {"Hearts": 0, "Diamonds": 2, "Clubs": 1, "Spades": 3}
VALUE_ORDER = {
    "2": 7,
    "3": 10,
    "4": 4,
    "5": 5,
    "6": 11,
    "7": 3,
    "8": 2,
    "9": 13,
    "10": 6,
    "J": 1,
    "Q": 9,
    "K": 12,
    "A": 8,
}
NUM_WINDOW_ROUNDS = 1

def playing(player, deck):
    """
    Playing strategy goes here (what card will the player expose to their partner)
    """
    if not player.hand:
        return None

    hand_indices = [get_card_index(card) for card in player.hand]
    round = len(player.played_cards) + 1
    
    if round <= NUM_WINDOW_ROUNDS:
        card_to_play_index = get_best_window_lower_bound(hand_indices)
    else:
        card_to_play_index = get_max_card(hand_indices)

    return card_to_play_index


def get_card_index(card):
    """
    This function maps cards to an index and scrambles the index.
    """
    # Hash formula that combines suit and value in a less predictable way
    suit = SUIT_ORDER[card.suit]
    value = VALUE_ORDER[card.value]

    index = suit * 13 + value
    return index

def get_max_card(hand_indices):
    """
    Play card with the highest index to create upper bound value.
    """
    max_index = hand_indices.index(max(hand_indices))
    return max_index

def use_max_value_index(player, g_cards):
    """
    Use the upper bound value strategy to inform guess
    """
    # Take card exposed by partner and use it to inform the rest of our guesses
    partner_exposed_card = player.exposed_cards[PARTNERS[player.name]][-1]
    max_index = get_card_index(partner_exposed_card)

    guess_indices = [get_card_index(card) for card in g_cards]

    index_filter = []
    for i, guess_index in enumerate(guess_indices):
        if guess_index<max_index:
            index_filter.append(i)

    below_max_cards = [g_cards[i] for i in index_filter]
    return below_max_cards

def get_guessable_cards(player, cards):
    # Remove cards that in the player's hand
    g_cards = list(set(cards) - set(player.hand))
    # Remove cards that have been exposed in gameplay
    for _, exposed in player.exposed_cards.items():
        g_cards = list(set(g_cards) - set(exposed))
    return g_cards

def clean_guess_history(player, s_cards):
    cleaned_guesses = []
    cleaned_cvals = []
    for r in range(0, len(player.guesses)):
        r_guess = player.guesses[r]
        cleaned_guess = [g for g in r_guess if g in s_cards]

        # We need to decrement the cValue from our guess for every card that our partner has exposed from their hand that was in the guess.
        cval_adjustment = 0
        for partner_exposed in player.exposed_cards[PARTNERS[player.name]]:
            if partner_exposed in cleaned_guess:
                cval_adjustment += 1

        # If cards were removed from the round also adjust the cValue
        adj_cval = player.cVals[r] - cval_adjustment

        # Write out the adjusted round
        cleaned_guesses = cleaned_guesses + [cleaned_guess]
        cleaned_cvals = cleaned_cvals + [adj_cval]

    return cleaned_guesses, cleaned_cvals

def get_card_prob(player, s_cards, round):

    P = 13 - round    # Number of cards in your Partner's hand
    T = len(s_cards)  # Number of cards that could be in partner's hand based on Strategy (all possible cards to build our guess from)
    probs = [1 / T] * T

    cleaned_guesses, cleaned_cvals = clean_guess_history(player, s_cards)

    if P == T or round == 1:
        return probs

    if player.guesses:
        # Get cValue from previous round
        C = player.cVals[round - 2]  # Minus 2 because first round is skipped so index at Round 2 starts at 0.
        # Remove historical guesses that are no longer valid before calculating probabilities
        guess = player.guesses[round - 2]
        adj_guess = [card for card in guess if card in s_cards]
        G = len(adj_guess) # Number of guesses made that can be used with the cvalue.

        if G == 0:
            return probs

        # There are cases where the previous guesses have had cards eliminated to the cvalue given is higher than the number of cards that are possible to include in our guess.
        if C >= G or T <= P:
            prob_guessed_card = 1
            prob_not_guessed_card = 0.001
            total_prob = prob_guessed_card * P
        else:
            prob_guessed_card = C / G  # Probability for each guessed card
            prob_not_guessed_card = (G - C) / (T - P)  # Probability for each unguessed card
            total_prob = prob_guessed_card * P + prob_not_guessed_card * (T - P)

        # Normalize probabilities to ensure they sum to 1
        prob_guessed_card /= total_prob
        prob_not_guessed_card /= total_prob

        # Add these probabilities to a list
        probs = []
        for card in s_cards:
            if card in adj_guess:
                probs.append(prob_guessed_card)
            else:
                probs.append(prob_not_guessed_card)

        # Add a check to ensure the probabilities sum to 1
        total_sum = sum(probs)
        if total_sum != 1:
            # force to renomrmalize
            probs = [p / total_sum for p in probs]

    return probs

def guessing(player, cards, round):
    """
    Guessing strategy based on ranking guessable cards from highest to lowest probability 
    and selecting top N guesses.

    :param player: The Player object.
    :param cards: List of all Card objects in the game.
    :param round: Integer representing the current round number.
    :return: List of guessed Card objects.
    """
    # Determine the number of guesses needed
    num_guesses = 13 - round

    if num_guesses <= 0:
        return []

    # Remove cards from list that are not valid guesses for this round.
    g_cards = get_guessable_cards(player, cards)

    if round <= NUM_WINDOW_ROUNDS:
        selected_guesses = use_best_window_lower_bound(player, g_cards)
        return selected_guesses

    # Apply strategy to narrow possible cards
    s_cards = use_max_value_index(player, g_cards)

    if not s_cards:
        return []

    # Update probability of possible cards
    p_cards = get_card_prob(player, s_cards, round)

    if not p_cards or len(p_cards) != len(s_cards):
        p_cards = [1 / len(s_cards)] * len(s_cards)

    # Pair each card with its probability
    card_prob_pairs = list(zip(s_cards, p_cards))

    # Sort the pairs based on probability in descending order
    sorted_pairs = sorted(card_prob_pairs, key=lambda pair: pair[1], reverse=True)

    # Select the top N cards based on the current round
    selected_guesses = [card for card, prob in sorted_pairs[:num_guesses]]

    return selected_guesses

def use_best_window_lower_bound(player, g_cards, window=12, highest=52):
    # get the last exposed card from the partner
    partner_exposed_card = player.exposed_cards[PARTNERS[player.name]][-1]
    # find the leftmost index of that sliding window
    sliding_window_leftmost_index = get_card_index(partner_exposed_card)

    # Get all cards in your hand that are in the window above the card that was exposed (a lower bound)
    g_card_indices = [get_card_index(card) for card in g_cards]

    guess = [val for val in g_card_indices if sliding_window_leftmost_index < val]
    guess.sort()
    # Fewer that the 12 guesses needed we take cards from the wrapped around bottom of the index range
    if len(guess) < window:
        max_window = window - len(guess)
        g_card_indices.sort()
        guess = guess + g_card_indices[:max_window]
    else:
        guess = guess[:window]

    original_g_card_indices = [g_card_indices.index(g) for g in guess]
    selected_guesses = [g_cards[i] for i in original_g_card_indices]
    return selected_guesses

def get_best_window_lower_bound(hand_indices, window=13, highest=52):
    """
    Determines the lower bound index of the sliding window with the most cards in current player's hand.
    """
    if not hand_indices:
        return 0  # Default lower bound when hand is empty

    hand_sorted = sorted(hand_indices)
    min_window = 0
    max_cards_in_window = 0

    for min_card in hand_sorted:
        # Define the window range, wrapping around if necessary
        window_end = min_card + window - 1
        if window_end > highest:
            # wrap around
            window_range = list(range(min_card+1, highest + 1)) + list(range(0, window_end - highest))
        else:
            window_range = list(range(min_card+1, min_card + window))

        # count how many hand cards are within the window
        cards_in_window = set(hand_sorted).intersection(set(window_range))
        num_cards = len(cards_in_window)

        if num_cards > max_cards_in_window:
            max_cards_in_window = num_cards
            min_window = min_card

    if min_window == 0:
        min_window = random.choice(hand_indices)
    return hand_indices.index(min_window)