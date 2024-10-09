import random
from CardGame import Deck

RANDOM_SEED = 110248341

PARTNER_MAP = {
    "North": "South", 
    "East": "West", 
    "South": "North", 
    "West": "East"
}

def playing(player, deck):
    """
    Playing min/max boundaries strategy.
    
    Returns an integer representing the index of the card in the player's hand to play.
    """
    if not player.hand:
        return None

    cards_to_indices, _ = create_card_to_index_mapping(RANDOM_SEED, Deck().cards)
    turn = 14 - len(player.hand)

    if turn % 2 == 1:
        # on odd turns, expose the card with the highest index value
        bound_card = max(player.hand, key=lambda card: cards_to_indices[card])
    else:
        # on even turns, expose the card with the lowest index value
        bound_card = min(player.hand, key=lambda card: cards_to_indices[card])
    
    return player.hand.index(bound_card)

def guessing(player, cards, round):
    """
    Returns a list of n Card objects to guess partner's hand, incorporating feedback from previous guesses.
    """
    card_probs_by_index = {index: 1 for index in range(1, 53)}
    partner = PARTNER_MAP[player.name]

    cards_to_indices, indices_to_cards = create_card_to_index_mapping(RANDOM_SEED, Deck().cards)

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
    for i in range(len(partner_cards_exposed)):
        bound = cards_to_indices[partner_cards_exposed[i]]
        if (i + 1) % 2 == 1:
            indices_to_delete = [index for index in card_probs_by_index if index > bound]
        else:
            indices_to_delete = [index for index in card_probs_by_index if index < bound]
        
        for index in indices_to_delete:
            del card_probs_by_index[index]

    # Update card probabilities based on previous guesses
    card_probs_by_index = update_probs_from_guesses(card_probs_by_index, player, partner_cards_exposed, all_other_cards_exposed, cards_to_indices)

    # Determine your guesses by finding n cards with highest probabilities
    n = 13 - round
    sorted_card_probs_by_index = sorted(card_probs_by_index, key=card_probs_by_index.get, reverse=True)
    top_n_card_prob_indices = sorted_card_probs_by_index[:n]
    random.shuffle(top_n_card_prob_indices)

    card_guesses = []
    for index in top_n_card_prob_indices:
        card_guesses.append(indices_to_cards[index])

    return card_guesses

def create_card_to_index_mapping(seed, cards):
    """
    Method which maps a card to a random index between 1-52.
    """
    random.seed(seed)
    indices = random.sample(range(1, 53), 52)

    cards_to_indices = {card: index for card, index in zip(cards, indices)}
    indices_to_cards = {index: card for card, index in cards_to_indices.items()}
    
    return cards_to_indices, indices_to_cards

def update_probs_from_guesses(card_probs_by_index, player, partner_cards_exposed, all_other_cards_exposed, cards_to_indices):
    """
    Adjusts the probabilities of remaining cards based on feedback from previous guesses.
    
    - If c_value is 0, set the probability of the guessed cards to 0.
    - If c_value is equal to the number of guesses, set the probability of the guessed cards to infinity.
    - For partial correctness (0 < c_value < total_guesses), adjust probabilities based on the correctness ratio.
    """
    
    for guesses, c_value in zip(player.guesses, player.cVals):
        # Number of cards guessed in this round
        total_guesses = len(guesses)
        
        if total_guesses == 0:
            continue  # Skip if there are no guesses

        # If all guesses are correct, set their probability to infinity
        if c_value == total_guesses:
            for card in guesses:
                card_index = cards_to_indices[card]
                if card_index in card_probs_by_index:
                    card_probs_by_index[card_index] = float('inf')  # Set to infinity
        # If none are correct, set their probability to 0
        elif c_value == 0:
            for card in guesses:
                card_index = cards_to_indices[card]
                if card_index in card_probs_by_index:
                    card_probs_by_index[card_index] = 0  # Set probability to 0
        # Partial correctness: adjust probabilities proportionally
        else:
            correct_ratio = c_value / total_guesses
            for card in guesses:
                card_index = cards_to_indices[card]
                if card_index in card_probs_by_index:
                    # Use the correct_ratio to decide the increase or decrease
                    if correct_ratio > 0.35:
                        card_probs_by_index[card_index] *= 1.1  # Increase probability
                    else:
                        card_probs_by_index[card_index] *= 0.9  # Decrease probability

    return card_probs_by_index
