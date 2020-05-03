
import random
import re
from collections import Counter


class GameEvent(Exception):
    """Base game event class."""
    pass


class QuitGame(GameEvent):
    """Quit game event."""
    pass


class RestartGame(GameEvent):
    """Restart game event."""
    pass


class GameCore:
    """Core game class

    Don't work by itself. Have to be equiped with input-output methods.
    """

    DIFFICULTIES = {
        'easy': {
            'possible_digits': set('123456'),
            'digits_range': '1-6',
            'number_size': 3,
        },
        'normal': {
            'possible_digits': set('123456789'),
            'digits_range': '1-9',
            'number_size': 4,
        },
        'hard': {
            'possible_digits': set('123456789abcdf'),
            'digits_range': '1-9,a-f',
            'number_size': 5,
        },
    }


    def __init__(self):
        self.difficulty = None
        self.number_size = None
        self.possible_digits = None
        self.digits_range = None
        self.number = None
        self.steps = None


    def draw_number(self):
        """Draw number digits from self.possible_digits."""
        self.number = ''.join(
            random.sample(self.possible_digits, self.number_size)
        )


    def set_difficulty(self, difficulty=None):
        """Setting game difficulty.

        Ask user if not given directly.
        """
        # Ask for difficulty if not given directly
        if difficulty is None:
            self.difficulty = self.difficulty_selection()
        else:
            self.difficulty = difficulty

        # Setting difficulty
        mode = self.DIFFICULTIES[self.difficulty]
        self.number_size = mode['number_size']
        self.possible_digits = mode['possible_digits']
        self.digits_range = mode['digits_range']


    def comput_bullscows(self, guess):
        """Return bulls and cows for given string comparing to self."""
        bulls, cows = 0, 0

        for i in range(self.number_size):
            if re.match(guess[i], self.number[i], flags=re.I):
                bulls += 1
            elif re.search(guess[i], self.number, flags=re.I):
                cows += 1

        return {'bulls': bulls, 'cows': cows}


    def is_number_syntax_corect(self, number):
        """Check if given string have correct syntax and can be compared to self."""

        iscorrect = True

        # Check if number have wrong characters
        wrong_chars = set(number) - self.possible_digits
        if wrong_chars:
            self.wrong_characters_in_number_message(
                wrong_chars,
                number,
            )
            iscorrect = False

        # Check length
        if len(number) != self.number_size:
            self.wrong_length_of_number_message(len(number))
            iscorrect = False

        # Check that digits don't repeat
        digits = Counter(number)
        repeated_digits = {i for i, n in digits.items() if n > 1}
        repeated_digits -= wrong_chars
        if repeated_digits:
            self.repeated_digits_in_number_message(repeated_digits)
            correct = False

        return iscorrect


    def round(self):
        """Round method.

        Handle inserting answers, viewing results and GemeEvents.
        """
        self.initing_round()
        while True: # Round loop
            try:
                input_ = self.take_number()
            except (RestartGame, QuitGame):
                self.ending_round()
                raise

            bullscows = self.comput_bullscows(input_)
            if bullscows['bulls'] == self.number_size:
                self.game_score_message()
                self.ending_round()
                return

            self.bulls_and_cows_message(bullscows)

            self.steps += 1


    def play(self):
        """Starts game.

        Handle multi-round game, setting difficulty, drawing number.
        """
        if self.difficulty is None:
            self.set_difficulty()

        while True: # Game loop
            self.draw_number()
            print(self.number) # TESTING PRINT
            self.steps = 1
            try:
                self.round()
            except RestartGame:
                continue
            except QuitGame:
                return

            if self.ask_if_continue_playing():
                continue
            else:
                return
