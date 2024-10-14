import random
import time
import math
from CardGame import Card

RANDOM_SEED = 11024890

PARTNER_MAP = {
    "North": "South",
    "East": "West",
    "South": "North",
    "West": "East",
}

def playing(player, deck):
    """
    Playing min/max boundaries strategy.
    
    Returns an integer representing the index of the card in the player's hand to play.
    """
    if not player.hand:
        return None

    deck = get_deck_of_cards()
    cards_to_indices, _ = create_card_to_index_mapping(RANDOM_SEED, deck)
    turn = 14 - len(player.hand)

    if turn < 9:
        # play greedy min/max variant
        prev_min = 0
        prev_max = 53
        for card in player.played_cards:
            if (cards_to_indices[card] - prev_min) < (prev_max - cards_to_indices[card]):
                prev_min = cards_to_indices[card]
            else:
                prev_max = cards_to_indices[card]

        curr_min_card = min(player.hand, key=lambda card: cards_to_indices[card])
        curr_max_card = max(player.hand, key=lambda card: cards_to_indices[card])

        if (cards_to_indices[curr_min_card] - prev_min) > (prev_max - cards_to_indices[curr_max_card]):
            card_to_play = curr_min_card
        else:
            card_to_play = curr_max_card
    elif turn % 2 == 0:
        # on even turns, play card with highest index value
        card_to_play = max(player.hand, key=lambda card: cards_to_indices[card])
    else:
        # on odd turns, play card with lowest index value
        card_to_play = min(player.hand, key=lambda card: cards_to_indices[card])
    
    return player.hand.index(card_to_play)

def guessing(player, cards, round):
    """
    Returns a list of n Card objects to guess partner's hand, incorporating feedback from previous guesses.
    """
    card_probs_by_index = {index: 1/52 for index in range(1, 53)}
    partner = PARTNER_MAP[player.name]

    deck = get_deck_of_cards()
    cards_to_indices, indices_to_cards = create_card_to_index_mapping(RANDOM_SEED, deck)

    all_other_cards_exposed = []
    partner_cards_exposed = []
    for player_name, cards in player.exposed_cards.items():
        if player_name == partner:
            partner_cards_exposed += cards
        else:
            all_other_cards_exposed += cards
    
    # Delete cards of your own
    for own_card in list(set(player.hand)):
        del card_probs_by_index[cards_to_indices[own_card]]
    
    # Delete cards which have been previously exposed
    for exposed_card in (set(partner_cards_exposed) | set(all_other_cards_exposed)):
        del card_probs_by_index[cards_to_indices[exposed_card]]

    # Delete cards based on partner's min/max boundary information
    prev_min = 0
    prev_max = 53
    for turn in range(len(partner_cards_exposed)):
        played_card = cards_to_indices[partner_cards_exposed[turn]]
        if (turn + 1) < 9:
            # partner playing greedy min/max
            if (played_card - prev_min) < (prev_max - played_card):
                # partner played a minimum card
                prev_min = played_card
                indices_to_delete = [index for index in card_probs_by_index if index < played_card]
            else:
                # partner played a maximum card
                prev_max = played_card
                indices_to_delete = [index for index in card_probs_by_index if index > played_card]
        elif (turn + 1) % 2 == 0:
            indices_to_delete = [index for index in card_probs_by_index if index > played_card]
        else:
            indices_to_delete = [index for index in card_probs_by_index if index < played_card]

        for index in indices_to_delete:
            del card_probs_by_index[index]

    # Update card probabilities based on previous guesses
    card_probs_by_index = update_probs_from_guesses(card_probs_by_index, player, partner_cards_exposed, all_other_cards_exposed, cards_to_indices, indices_to_cards)

    # Determine your guesses by finding n cards with highest probabilities
    n = 13 - round
    sorted_card_probs_by_index = sorted(card_probs_by_index, key=card_probs_by_index.get, reverse=True)
    top_n_card_prob_indices = sorted_card_probs_by_index[:n]

    card_guesses = []
    for index in top_n_card_prob_indices:
        card_guesses.append(indices_to_cards[index])

    return card_guesses

def update_probs_from_guesses(card_probs_by_index, player, partner_cards_exposed, all_other_cards_exposed, cards_to_indices, indices_to_cards):
    """
    Adjusts the probabilities of remaining cards based on feedback from previous guesses.
    """
    for turn, (guess, c_val) in enumerate(zip(player.guesses, player.cVals)):
        guess = set(guess)
        all_other_cards_exposed = set(all_other_cards_exposed)
        correct_guess_count = c_val
        valid_guess_count = len(guess)

        exposed_card_count = 4
        for card in guess:
            if card in partner_cards_exposed:
                correct_guess_count -= 1
                valid_guess_count -= 1
                exposed_card_count -= 1
            if card in all_other_cards_exposed:
                valid_guess_count -= 1
                exposed_card_count -= 1
        
        valid_unguessed_count = 39 - 4*(turn+1) - len(guess) - exposed_card_count + 1

        # if player.name == "North":
        #     print(f"Numerator: {correct_guess_count}")
        #     print(f"Denominator: {valid_guess_count}")
        #     print(f"Guess probability = {correct_guess_count} / {valid_guess_count}")
        #     print(f"NonGuess probability = {12 - turn - c_val} / {valid_unguessed_count}")
        
        indices_to_delete = []
        for card in guess:
            card_idx = cards_to_indices[card]
            if card_idx in card_probs_by_index:
                if valid_guess_count > 0:
                    prob = correct_guess_count / valid_guess_count
                    if prob >= 0:
                        card_probs_by_index[card_idx] *= prob
                    else:
                        indices_to_delete.append(card_idx)

        for card_idx in card_probs_by_index:
            card = indices_to_cards[card_idx]
            if card not in guess:
                if valid_unguessed_count > 0:
                    prob = (len(guess) - c_val + 1) / valid_unguessed_count
                    if prob >= 0:
                        card_probs_by_index[card_idx] *= prob
                    else:
                        indices_to_delete.append(card_idx)
        
        for idx in indices_to_delete:
            del card_probs_by_index[idx]

    return card_probs_by_index

def create_card_to_index_mapping(seed, cards):
    """
    Method which maps a card to a random index between 1-52.
    """
    random.seed(seed)
    indices = random.sample(range(1, 53), 52)

    cards_to_indices = {card: index for card, index in zip(cards, indices)}
    indices_to_cards = {index: card for card, index in cards_to_indices.items()}
    
    return cards_to_indices, indices_to_cards

def get_deck_of_cards():
    suits = ["Hearts", "Diamonds", "Clubs", "Spades"]
    values = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
    
    return [Card(suit, value) for value in values for suit in suits]