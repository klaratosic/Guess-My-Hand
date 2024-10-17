import tkinter as tk
import random
import argparse
import importlib.util
from tqdm import tqdm
from copy import copy
from CardGame import Card, Deck, Player
import numpy as np
import logging
import functools
import io
import os
import sys
from contextlib import redirect_stdout
from player_strategies import NorthSouthStrategy, EastWestStrategy
from guessing_functions import NorthSouthGuess, EastWestGuess
import csv



class Game:
    def __init__(self, master, seed=42):
        self.master = master
        self.master.title("Guess My Hand")
        self.master.geometry("1200x800")
        self.seed = seed
        self.round = 1
        self.master.configure(bg='#2ecc71')
        self.deck = Deck(seed)
        self.copyCards = copy(self.deck.cards)
        self.players = [
            Player("North", NorthSouthStrategy),
            Player("East", EastWestStrategy),
            Player("South", NorthSouthStrategy),
            Player("West", EastWestStrategy)
        ]
        self.current_player = 0
        self.individual_scores = {"North": 0, "East": 0, "South": 0, "West": 0}
        self.partnership_scores = {"NS": 0, "EW": 0}
        self.setup_gui()
        self.deal_initial_cards(self.deck)
        self.update_display()

    def setup_gui(self):
        self.player_frames = []
        for i, player in enumerate(self.players):
            frame = tk.Frame(self.master, borderwidth=2, relief="ridge", bg='#27ae60')
            frame.grid(row=i//2 + 1, column=i%2, padx=10, pady=10, sticky="nsew")
            label = tk.Label(frame, text=player.name, font=("Arial", 14, "bold"), bg='#27ae60', fg='white')
            label.pack(pady=5)
            self.player_frames.append(frame)

        self.reset_button = tk.Button(self.master, text="Reset", command=self.reset_game, font=("Arial", 12), bg='black', fg='white')
        self.reset_button.grid(row=0, column=0, pady=10)

        self.step_button = tk.Button(self.master, text="Step", command=self.step, font=("Arial", 12), bg='black', fg='white')
        self.step_button.grid(row=0, column=0, columnspan=2, pady=10)

        self.play_all_button = tk.Button(self.master, text="Play All", command=self.play_all, font=("Arial", 12), bg='black', fg='white')
        self.play_all_button.grid(row=0, column=1, pady=10)

        self.played_cards_frame = tk.Frame(self.master, borderwidth=2, relief="ridge", bg='#27ae60')
        self.played_cards_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.played_cards_label = tk.Label(self.played_cards_frame, text="Played Cards:", font=("Arial", 14, "bold"), bg='#27ae60', fg='white')
        self.played_cards_label.pack(pady=5)

        self.played_cards_columns = []
        for player in self.players:
            column = tk.Frame(self.played_cards_frame, bg='#27ae60')
            column.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=5)
            tk.Label(column, text=player.name, font=("Arial", 12), bg='#27ae60', fg='white').pack()
            self.played_cards_columns.append(column)

        self.score_frame = tk.Frame(self.master, borderwidth=2, relief="ridge", bg='#27ae60')
        self.score_frame.grid(row=5, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

        self.individual_score_frame = tk.Frame(self.score_frame, bg='#27ae60')
        self.individual_score_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=10)
        tk.Label(self.individual_score_frame, text="Individual Scores", font=("Arial", 14, "bold"), bg='#27ae60', fg='white').pack(pady=5)

        self.individual_score_labels = {}
        ns_frame = tk.Frame(self.individual_score_frame, bg='#27ae60')
        ns_frame.pack(fill=tk.X)
        ew_frame = tk.Frame(self.individual_score_frame, bg='#27ae60')
        ew_frame.pack(fill=tk.X)

        self.individual_score_labels["North"] = tk.Label(ns_frame, text="North: 0", font=("Arial", 12), bg='#27ae60', fg='white')
        self.individual_score_labels["North"].pack(side=tk.LEFT, expand=True)
        self.individual_score_labels["South"] = tk.Label(ns_frame, text="South: 0", font=("Arial", 12), bg='#27ae60', fg='white')
        self.individual_score_labels["South"].pack(side=tk.LEFT, expand=True)
        self.individual_score_labels["East"] = tk.Label(ew_frame, text="East: 0", font=("Arial", 12), bg='#27ae60', fg='white')
        self.individual_score_labels["East"].pack(side=tk.LEFT, expand=True)
        self.individual_score_labels["West"] = tk.Label(ew_frame, text="West: 0", font=("Arial", 12), bg='#27ae60', fg='white')
        self.individual_score_labels["West"].pack(side=tk.LEFT, expand=True)

        self.partnership_score_frame = tk.Frame(self.score_frame, bg='#27ae60')
        self.partnership_score_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH, padx=5)
        tk.Label(self.partnership_score_frame, text="Partnership Scores", font=("Arial", 14, "bold"), bg='#27ae60', fg='white').pack(pady=5)

        self.ns_score_label = tk.Label(self.partnership_score_frame, text="NS: 0", font=("Arial", 12), bg='#27ae60', fg='white')
        self.ns_score_label.pack()
        self.ew_score_label = tk.Label(self.partnership_score_frame, text="EW: 0", font=("Arial", 12), bg='#27ae60', fg='white')
        self.ew_score_label.pack()

        self.guesses_frame = tk.Frame(self.master, borderwidth=2, relief="ridge", bg='#27ae60')
        self.guesses_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        tk.Label(self.guesses_frame, text="Guesses", font=("Arial", 14, "bold"), bg='#27ae60', fg='white').pack(pady=5)
        

        self.status_label = tk.Label(self.master, text="", font=("Arial", 12), bg='#2ecc71', fg='white')
        self.status_label.grid(row=6, column=0, columnspan=2, pady=10)

        for i in range(2):
            self.master.grid_columnconfigure(i, weight=1)
        for i in range(7):
            self.master.grid_rowconfigure(i, weight=1)

    def deal_initial_cards(self, deck):
        for _ in range(13):  # Deal 13 cards to each player
            for player in self.players:
                player.draw(self.deck)
        for player in self.players:
            player.hand = sorted(player.hand, key=lambda element: deck.values.index(element.value))

    def update_display(self):
        for i, player in enumerate(self.players):
            for widget in self.player_frames[i].winfo_children()[1:]:
                widget.destroy()
            card_frame = tk.Frame(self.player_frames[i], bg='#27ae60')
            card_frame.pack(fill=tk.BOTH, expand=True)
            for j, card in enumerate(player.hand):
                color = 'red' if card.suit in ["Hearts", "Diamonds"] else 'black'
                tk.Label(card_frame, text=f"{card.map[card.suit]}{card.value}", font=("Arial", 12), bg='#27ae60', fg=color).pack(side=tk.LEFT, padx=2)

        for i, column in enumerate(self.played_cards_columns):
            for widget in column.winfo_children()[1:]:
                widget.destroy()
            played_cards = self.players[i].played_cards
            for j, card in enumerate(played_cards):
                color = 'red' if card.suit in ["Hearts", "Diamonds"] else 'black'
                tk.Label(column, text=f"{card.map[card.suit]}{card.value}", font=("Arial", 12), bg='#27ae60', fg=color).pack()

        for player_name, score in self.individual_scores.items():
            self.individual_score_labels[player_name].config(text=f"{player_name}: {score}")

        self.ns_score_label.config(text=f"NS: {self.partnership_scores['NS']}")
        self.ew_score_label.config(text=f"EW: {self.partnership_scores['EW']}")

    def reset_game(self):
        self.round = 1
        self.deck = Deck(self.seed)
        self.copyCards = copy(self.deck.cards)
        self.players = [
            Player("North", NorthSouthStrategy),
            Player("East", EastWestStrategy),
            Player("South", NorthSouthStrategy),
            Player("West", EastWestStrategy)
        ]
        self.current_player = 0
        self.individual_scores = {"North": 0, "East": 0, "South": 0, "West": 0}
        self.partnership_scores = {"NS": 0, "EW": 0}
        self.deal_initial_cards(self.deck)
        self.step_button.config(state="normal")
        self.play_all_button.config(state="normal")
        self.update_display()
        self.status_label.config(text="Game reset. Click 'Step' to start a new round.")

        # Reset guesses
        for widget in self.guesses_frame.winfo_children()[1:]:
            widget.destroy()

    def step(self):
        print(f"Round {self.round}")
        for i, player in enumerate(self.players):
            card_index = player.strategy(player, self.deck)
            played_card = player.play_card(card_index)
            print(player.name, played_card.value, played_card.suit)
            # Update exposed cards for other players
            for j, other_player in enumerate(self.players):
                other_player.update_exposed_cards(player.name, played_card)
        
        northGuess = NorthSouthGuess(self.players[0], self.copyCards, self.round)
        self.players[0].guesses.append(northGuess)
        eastGuess = EastWestGuess(self.players[1], self.copyCards, self.round)
        self.players[1].guesses.append(eastGuess)
        southGuess = NorthSouthGuess(self.players[2], self.copyCards, self.round)
        self.players[2].guesses.append(southGuess)
        westGuess = EastWestGuess(self.players[3], self.copyCards, self.round)
        self.players[3].guesses.append(westGuess)
        for widget in self.guesses_frame.winfo_children()[1:]:
            widget.destroy()

        # Update guess labels with colored cards
        for player_name, guess in zip(["North", "East", "South", "West"], [northGuess, eastGuess, southGuess, westGuess]):
            guess_frame = tk.Frame(self.guesses_frame, bg='#27ae60')
            guess_frame.pack(fill=tk.X)
            guess = sorted(guess, key=lambda element: self.deck.values.index(element.value))
            tk.Label(guess_frame, text=f"{player_name}: ", font=("Arial", 12), bg='#27ae60', fg='white').pack(side=tk.LEFT)
            for card in guess:
                color = 'red' if card.suit in ["Hearts", "Diamonds"] else 'black'
                tk.Label(guess_frame, text=f"{card.map[card.suit]}{card.value}", font=("Arial", 12), bg='#27ae60', fg=color).pack(side=tk.LEFT, padx=2)

        cNorth = len(set(northGuess).intersection(set(self.players[2].hand)))
        self.players[0].cVals.append(cNorth)
        cEast = len(set(eastGuess).intersection(set(self.players[3].hand)))
        self.players[1].cVals.append(cEast)
        cSouth = len(set(southGuess).intersection(set(self.players[0].hand)))
        self.players[2].cVals.append(cSouth)
        cWest = len(set(westGuess).intersection(set(self.players[1].hand)))
        self.players[3].cVals.append(cWest)

        self.individual_scores["North"] = cNorth
        self.individual_scores["East"] = cEast
        self.individual_scores["South"] = cSouth
        self.individual_scores["West"] = cWest
        self.partnership_scores["NS"] += cNorth + cSouth
        self.partnership_scores["EW"] += cEast + cWest

        print("-"*100)
        self.update_display()

        if self.is_game_over():
            self.end_game()
        else:
            self.status_label.config(text=f"Round {self.round} completed. Click 'Step' for the next round.")
            self.round += 1

    def play_all(self):
        while not self.is_game_over():
            self.step()
        self.end_game()

    def is_game_over(self):
        return all(len(player.hand) == 0 for player in self.players)

    def end_game(self):
        self.status_label.config(text=f"Game Over: All cards have been played! Total rounds: {self.round}")
        self.step_button.config(state="disabled")
        self.play_all_button.config(state="disabled")
        self.reset_button.config(state="normal")

def import_class_from_file(folder, file_name, class_name):
    file_path = f"{folder}/{file_name}.py"
    spec = importlib.util.spec_from_file_location(file_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[file_name] = module
    spec.loader.exec_module(module)
    return getattr(module, class_name)

def setup_logger(flag):
    logger = logging.getLogger(flag)
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(f"{flag}_log.txt")
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger

def log_output(flag):
    logger = setup_logger(flag)
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            original_stdout = sys.stdout
            sys.stdout = io.StringIO()
            try:
                result = func(*args, **kwargs)
                output = sys.stdout.getvalue()
                if output:
                    logger.info(f"Function {func.__name__} output:\n{output}")
                return result
            finally:
                sys.stdout = original_stdout
        return wrapper
    return decorator

def create_logged_function(func, flag):
    return log_output(flag)(func)

def log_results(ns, ew, score_p1, score_p2, seed):
    filename = 'tournaments.csv'
    file_exists = os.path.isfile(filename)
    
    with open(filename, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(['P1 [NS]', 'P2 [EW]', 'Score P1', 'Score P2', 'Seed'])
        writer.writerow([ns, ew, score_p1, score_p2, seed])

def run_game_without_gui(seed):
    deck = Deck(seed)
    # print("Seed: ", seed)
    players = [
        Player("North", NorthSouthStrategy),
        Player("East", EastWestStrategy),
        Player("South", NorthSouthStrategy),
        Player("West", EastWestStrategy)
    ]
    
    # Deal initial cards
    for _ in range(13):
        for player in players:
            player.draw(deck)
    
    # Play the game
    ns_score = 0
    ew_score = 0
    round = 1
    while any(len(player.hand) > 0 for player in players):
        for player in players:
            card_index = player.strategy(player, deck)
            played_card = player.play_card(card_index)
            for other_player in players:
                other_player.update_exposed_cards(player.name, played_card)
        
        idealGuessLen = 13 - round

        try:
            northGuess = NorthSouthGuess(players[0], deck.copyCards, round)
            if len(northGuess) > idealGuessLen:
                northGuess = northGuess[:idealGuessLen]
            players[0].guesses.append(northGuess)
            cNorth = len(set(northGuess).intersection(set(players[2].hand)))
        except:
            print("North guessing failed")
            players[0].guesses.append([random.sample(deck.copyCards, 13 - round)])
            cNorth = 0

        players[0].cVals.append(cNorth)

        try:
            eastGuess = EastWestGuess(players[1], deck.copyCards, round)
            if len(eastGuess) > idealGuessLen:
                eastGuess = eastGuess[:idealGuessLen]
            players[1].guesses.append(eastGuess)
            cEast = len(set(eastGuess).intersection(set(players[3].hand)))
        except:
            print("East guessing failed")
            players[1].guesses.append([random.sample(deck.copyCards, 13 - round)])
            cEast = 0

        players[1].cVals.append(cEast)

        try:
            southGuess = NorthSouthGuess(players[2], deck.copyCards, round)
            if len(southGuess) > idealGuessLen:
                southGuess = southGuess[:idealGuessLen]
            players[2].guesses.append(southGuess)
            cSouth = len(set(southGuess).intersection(set(players[0].hand)))

        except:
            print("South guessing failed")
            players[2].guesses.append([random.sample(deck.copyCards, 13 - round)])
            cSouth = 0

        players[2].cVals.append(cSouth)

        try:
            westGuess = EastWestGuess(players[3], deck.copyCards, round)
            if len(westGuess) > idealGuessLen:
                westGuess = westGuess[:idealGuessLen]
            players[3].guesses.append(westGuess)
            cWest = len(set(westGuess).intersection(set(players[1].hand)))

        except:
            print("West guessing failed")
            players[3].guesses.append([random.sample(deck.copyCards, 13 - round)])
            cWest = 0
        
        players[3].cVals.append(cWest)

        ns_score += cNorth + cSouth
        ew_score += cEast + cWest
        
        round += 1
    del deck, players
    return {"NS": ns_score, "EW": ew_score}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Guess My Hand")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for card shuffling")
    parser.add_argument('--nsStrategy', type=int, choices=range(0, 11), help='North-South Strategy (1-10)')
    parser.add_argument('--ewStrategy', type=int, choices=range(0, 11), help='East-West Strategy (1-10)')
    parser.add_argument('--nsGuesses', type=int, choices=range(0, 11), help='North-South Guesses (1-10)')
    parser.add_argument('--ewGuesses', type=int, choices=range(0, 11), help='East-West Guesses (1-10)')
    parser.add_argument('--nSims', type=int, help='Number of simulations to run without GUI')
    parser.add_argument('--log', type=bool, default=False, help='Log the results to a txt in folder')
    args = parser.parse_args()

    folder = "teams"

    # Import strategies based on flag values
    if args.nsStrategy in range(0, 11):
        file_name = f"strategies_{args.nsStrategy}"
        class_name = "playing"
        try:
            NorthSouthStrategy = import_class_from_file(folder, file_name, class_name)
        except:
            print("North South Strategy import failed. Using the default strategy")
            pass
        if args.log:
            NorthSouthStrategy = create_logged_function(NorthSouthStrategy, f"./log-results/team{args.nsStrategy}-nsStrategy")

    if args.ewStrategy in range(0, 11):
        file_name = f"strategies_{args.ewStrategy}"
        class_name = "playing"
        try:
            EastWestStrategy = import_class_from_file(folder, file_name, class_name)
        except:
            print("East West Strategy import failed. Using the default strategy")
            pass
        if args.log:
            EastWestStrategy = create_logged_function(EastWestStrategy, f"./log-results/team{args.ewStrategy}-ewStrategy")

    if args.nsGuesses in range(0, 11):
        file_name = f"strategies_{args.nsGuesses}"
        class_name = "guessing"
        try:
            NorthSouthGuess = import_class_from_file(folder, file_name, class_name)
        except:
            print("North South Guesses import failed. Using the default strategy")
            pass
        if args.log:
            NorthSouthGuess = create_logged_function(NorthSouthGuess, f"./log-results/team{args.nsGuesses}-nsGuesses")

    if args.ewGuesses in range(0, 11):
        file_name = f"strategies_{args.ewGuesses}"
        class_name = "guessing"
        try:
            EastWestGuess = import_class_from_file(folder, file_name, class_name)
        except:
            print("East West guesses import failed. Using the default strategy")
            pass
        
        if args.log:
            EastWestGuess = create_logged_function(EastWestGuess, f"./log-results/team{args.ewGuesses}-ewGuesses")


    if args.nSims:
        # get consistent sequence of simulations given the seed
        seed = args.seed
        partnership_scoresNS = []
        partnership_scoresEW = []
        for i in tqdm(range(args.nSims)):
            scores = run_game_without_gui(seed)
            partnership_scoresNS.append(scores["NS"])
            partnership_scoresEW.append(scores["EW"])
            log_results(args.nsStrategy, args.ewStrategy, scores["NS"], scores["EW"], seed)
            seed += 1
        
        avg_scores = {
            "NS": np.mean(partnership_scoresNS),
            "EW": np.mean(partnership_scoresEW)
        }
        std_scores = {
            "NS": np.std(partnership_scoresNS),
            "EW": np.std(partnership_scoresEW)
        }
        print(f"Scores over {args.nSims} simulations:")
        print(f"NS Mean: {avg_scores['NS']:.2f} | NS Std Dev: {std_scores['NS']:.2f}")
        print(f"EW Mean: {avg_scores['EW']:.2f} | EW Std Dev: {std_scores['EW']:.2f}")
    else:
        print("Running GUI version...")
        import tkinter as tk
        root = tk.Tk()
        game = Game(root, seed=args.seed)
        root.mainloop()



