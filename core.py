"""This file keep core game classes"""

import random
import re
from collections import Counter
from abc import ABC, abstractmethod
from dataclasses import dataclass


# ========
# Events
# ========


class GameEvent(Exception):
    """Base game event class."""


class QuitGame(GameEvent):
    """Quit game event."""


class RestartGame(GameEvent):
    """Restart game event."""


class CancelOperation(GameEvent):
    """Operation canceled event."""


# ============
# Core classes
# ============


@dataclass(frozen=True)
class Difficulty:
    """Game difficulty parameters."""
    name: str
    digs_set: frozenset
    digs_range: str
    num_size: int


class AbstractRound(ABC):
    """Abstract Round class."""

    def __init__(self, difficulty):
        self.set_difficulty(difficulty)
        self._draw_number()
        #print(self._number) # TESTING PRINT
        self._steps = None

    def set_difficulty(self, difficulty):
        """Setting difficulty."""
        self._difficulty = difficulty.name
        self._num_size = difficulty.num_size
        self._digs_set = difficulty.digs_set
        self._digs_range = difficulty.digs_range

    def _draw_number(self):
        """Draw number digits from self._digs_set."""
        self._number = ''.join(
            random.sample(self._digs_set, self._num_size)
        )

    def _loop(self):
        """Round main loop."""
        self._steps = 1
        while True:
            bulls, cows = self._comput_bullscows(self._number_input())

            if bulls == self._num_size:
                self._score_output()
                return

            self._bulls_and_cows_output(bulls, cows)
            self._steps += 1

    def run(self):
        self._start_round()
        try:
            self._loop()
        finally:
            self._end_round()

    def _comput_bullscows(self, guess):
        """Return bulls and cows for given input."""
        bulls, cows = 0, 0

        for i in range(self._num_size):
            if guess[i] == self._number[i]:
                bulls += 1
            elif re.search(guess[i], self._number):
                cows += 1

        return bulls, cows

    def is_number_valid(self, number, outputs=True):
        """Check if given number string is valid."""

        is_correct = True

        # Check if number have wrong characters
        wrong_chars = set(number) - self._digs_set
        if wrong_chars:
            is_correct = False
            if outputs:
                self._wrong_chars_in_num_output(wrong_chars, number)

        # Check length
        if len(number) != self._num_size:
            is_correct = False
            if outputs:
                self._wrong_num_len_output(len(number))

        # Check that digits don't repeat
        digits = Counter(number)
        rep_digs = {i for i, n in digits.items() if n > 1}
        rep_digs -= wrong_chars
        if rep_digs:
            is_correct = False
            if outputs:
                self._rep_digs_in_num_output(rep_digs, number)

        return is_correct

    @abstractmethod
    def _start_round(self):
        """Method runed at the start of the round."""

    @abstractmethod
    def _end_round(self):
        """Method runed at the end of the round."""

    @abstractmethod
    def _wrong_chars_in_num_output(self, wrong_chars, wrong_input):
        """Output for wrong chars detected in given number.

        Method runed by self.is_number_valid."""

    @abstractmethod
    def _wrong_num_len_output(self, length):
        """Output for wrong length of given number.

        Method runed by self.is_number_valid."""

    @abstractmethod
    def _rep_digs_in_num_output(self, rep_digs, wrong_input):
        """Output for repeated digits in given number.

        Method runed by self.is_number_valid."""

    @abstractmethod
    def _number_input(self):
        """Number input"""

    @abstractmethod
    def _bulls_and_cows_output(self, bulls, cows):
        """Bulls and cows output"""

    @abstractmethod
    def _score_output(self):
        """Score output"""


class AbstractGame(ABC):
    """Abstract game class."""

    DIFFICULTIES = [Difficulty(*record) for record in (
        ('easy',   frozenset('123456'),         '1-6',     3),
        ('normal', frozenset('123456789'),      '1-9',     4),
        ('hard',   frozenset('123456789abcdf'), '1-9,a-f', 5),
    )]

    def __init__(self, Round, difficulty=None):
        self.Round = Round
        if difficulty is not None:
            self.set_difficulty(difficulty)
        else:
            self._difficulty = None

    def set_difficulty(self, difficulty=None):
        """Setting game difficulty.

        Ask user if not given directly.
        Prevent from set None when self.difficulty_input()
        raise CancelOperation.
        """
        # Ask for difficulty if not given directly
        if difficulty is None:
            difficulty = self.difficulty_input()

        self._difficulty = difficulty

    def _loop(self):
        """Main Game loop."""
        try:
            self.set_difficulty()
        except CancelOperation:
            return

        while True: # Game loop
            try:
                self.Round(self._difficulty).run()
            except RestartGame:
                continue
            except QuitGame:
                return

            try:
                if self._ask_if_continue_playing():
                    continue
                else:
                    return
            except CancelOperation:
                return

    def run(self):
        """Runs game loop.

        It is responsible to call self._start_game and self._end_game.
        """

        self._start_game()
        try:
            self._loop()
        finally:
            self._end_game()


    @abstractmethod
    def difficulty_input(self):
        """Difficulty input."""

    @abstractmethod
    def _start_game(self):
        """Method called at the start of the game."""

    @abstractmethod
    def _end_game(self):
        """Method called at the end of the game."""

    @abstractmethod
    def _ask_if_continue_playing(self):
        """Input to confirm to repeat round"""
