"""This file keep core game classes"""

import random
import re
from collections import Counter

from events import RestartGame, QuitGame, CancelOperation


class GameCore:
    """Core game class.

    Don't work by itself. Have to be equiped with input-output methods.
    """

    DIFFICULTIES = {
        'easy': {
            'digs_set': set('123456'),
            'digs_range': '1-6',
            'num_size': 3,
        },
        'normal': {
            'digs_set': set('123456789'),
            'digs_range': '1-9',
            'num_size': 4,
        },
        'hard': {
            'digs_set': set('123456789abcdf'),
            'digs_range': '1-9,a-f',
            'num_size': 5,
        },
    }


    def __init__(self, difficulty=None):
        if difficulty is not None:
            self.set_difficulty(difficulty)
        else:
            self.difficulty = None
            self.num_size = None
            self.digs_set = None
            self.digs_range = None
        self.number = None
        self.steps = None


    def draw_number(self):
        """Draw number digits from self.digs_set."""
        self.number = ''.join(
            random.sample(self.digs_set, self.num_size)
        )


    def set_difficulty(self, difficulty=None):
        """Setting game difficulty.

        Ask user if not given directly.
        """
        # Ask for difficulty if not given directly
        if difficulty is None:
            difficulty = self.difficulty_selection()

        self.difficulty = difficulty

        # Setting difficulty
        self.num_size = self.DIFFICULTIES[difficulty]['num_size']
        self.digs_set = self.DIFFICULTIES[difficulty]['digs_set']
        self.digs_range = self.DIFFICULTIES[difficulty]['digs_range']


    def comput_bullscows(self, guess):
        """Return bulls and cows for given input."""
        bulls, cows = 0, 0

        for i in range(self.num_size):
            if guess[i] ==  self.number[i]:
                bulls += 1
            elif re.search(guess[i], self.number):
                cows += 1

        return {'bulls': bulls, 'cows': cows}


    def is_number_valid(self, number):
        """Check if given number string is valid."""

        is_correct = True

        # Check if number have wrong characters
        wrong_chars = set(number) - self.digs_set
        if wrong_chars:
            self.wrong_characters_in_number_message(
                wrong_chars,
                number,
            )
            is_correct = False

        # Check length
        if len(number) != self.num_size:
            self.wrong_length_of_number_message(len(number))
            is_correct = False

        # Check that digits don't repeat
        digits = Counter(number)
        repeated_digits = {i for i, n in digits.items() if n > 1}
        repeated_digits -= wrong_chars
        if repeated_digits:
            self.repeated_digits_in_number_message(repeated_digits)
            correct = False

        return is_correct


    def round(self):
        """Round loop method."""
        self.start_round()
        while True: # Round loop
            try:
                input_ = self.take_number()
            except (RestartGame, QuitGame):
                self.end_round()
                raise

            bullscows = self.comput_bullscows(input_)
            if bullscows['bulls'] == self.num_size:
                self.score_message()
                self.end_round()
                return

            self.bulls_and_cows_message(bullscows)

            self.steps += 1


    def play(self):
        """Starts game.

        Handle multi-round game, setting difficulty, drawing number.
        """
        self.start_game()
        if self.difficulty is None:
            try:
                self.set_difficulty()
            except CancelOperation:
                self.end_game()
                return

        while True: # Game loop
            self.draw_number()
            print(self.number) # TESTING PRINT
            self.steps = 1
            try:
                self.round()
            except RestartGame:
                continue
            except QuitGame:
                self.end_game()
                return

            if self.ask_if_continue_playing():
                continue
            else:
                self.end_game()
                return
