"""This file keep core game classes"""

import random
import re
from collections import Counter
from abc import ABC, abstractmethod

from events import RestartGame, QuitGame, CancelOperation


class MetaGame(ABC):
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
            self._set_difficulty(difficulty)
        else:
            self.difficylty = None
            self.num_size = None
            self.digs_set = None
            self.digs_range = None
        self.number = None
        self.steps = None


    def _draw_number(self):
        """Draw number digits from self.digs_set."""
        self.number = ''.join(
            random.sample(self.digs_set, self.num_size)
        )


    def _set_difficulty(self, difficulty=None):
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


    def _comput_bullscows(self, guess):
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
            self._wrong_characters_in_number_message(
                wrong_chars,
                number,
            )
            is_correct = False

        # Check length
        if len(number) != self.num_size:
            self._wrong_length_of_number_message(len(number))
            is_correct = False

        # Check that digits don't repeat
        digits = Counter(number)
        repeated_digits = {i for i, n in digits.items() if n > 1}
        repeated_digits -= wrong_chars
        if repeated_digits:
            self._repeated_digits_in_number_message(repeated_digits)
            correct = False

        return is_correct


    def _round(self):
        """Round loop method."""
        self._start_round()
        while True: # Round loop
            try:
                input_ = self._take_number()
            except (RestartGame, QuitGame):
                self._end_round()
                raise

            bullscows = self._comput_bullscows(input_)
            if bullscows['bulls'] == self.num_size:
                self._score_message()
                self._end_round()
                return

            self._bulls_and_cows_message(bullscows)

            self.steps += 1


    def play(self):
        """Starts game.

        Handle multi-round game, setting difficulty, drawing number.
        """
        self._start_game()
        try:
            self._set_difficulty()
        except CancelOperation:
            self._end_game()
            return

        while True: # Game loop
            self._draw_number()
            print(self.number) # TESTING PRINT
            self.steps = 1
            try:
                self._round()
            except RestartGame:
                continue
            except QuitGame:
                self._end_game()
                return

            if self._ask_if_continue_playing():
                continue
            else:
                self._end_game()
                return

    @abstractmethod
    def difficulty_selection(self):
        """Difficulty input."""
        pass

    @abstractmethod
    def _wrong_characters_in_number_message(self, wrong_chars, wrong_input):
        """Output for wrong chars detected in given number.

        Method runed by is_number_valid."""
        pass

    @abstractmethod
    def _wrong_length_of_number_message(self, length):
        """Output for wrong length of given number.

        Method runed by is_number_valid."""
        pass

    @abstractmethod
    def _repeated_digits_in_number_message(self, rep_digs_list):
        """Output for repeated digits in given number.

        Method runed by is_number_valid."""
        pass

    @abstractmethod
    def _take_number(self):
        """Number input"""
        pass

    @abstractmethod
    def _score_message(self):
        """Score output"""
        pass

    @abstractmethod
    def _bulls_and_cows_message(self, bullscows):
        """Bulls and cows output"""
        pass

    @abstractmethod
    def _start_game(self):
        """Method runed at the start of the game."""
        pass

    @abstractmethod
    def _end_game(self):
        """Method runed at the end of the game."""
        pass

    def _start_round(self):
        """Method runed at the start of the round."""
        pass

    @abstractmethod
    def _end_round(self):
        """Method runed at the end of the round."""
        pass

    @abstractmethod
    def _ask_if_continue_playing(self):
        """Input to confirm to repeat round"""
        pass
