
import random
import re
from collections import Counter


class GameCore:
    """Core game class

    Don't work by itself. Have to be equiped with input-output methods.
    """

    DIFFICULTIES = {
        'easy': {
            'possible_digits': '123456',
            'digits_range': '1-6',
            'number_size': 3,
        },
        'normal': {
            'possible_digits': '123456789',
            'digits_range': '1-9',
            'number_size': 4,
        },
        'hard': {
            'possible_digits': '123456789ABCDEF',
            'digits_range': '1-9,A-F',
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

        # Other settings
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


    def is_number_syntax_corect(self, other):
        """Check if given string have correct syntax and can be compared to self."""

        # Check if number have wrong characters
        wrong_chars = {
            i for i in other
            if not re.search(i, self.possible_digits, re.I)
        }
        if wrong_chars:
            self.wrong_characters_in_number_message(
                wrong_chars,
                other,
            )
            return False

        # Check length
        if len(other) != self.number_size:
            self.wrong_length_of_number_message(other)
            return False

        # Check that digits don't repeat
        digits = Counter(other)
        repeated_digits = {i for i, n in digits.items() if n > 1}
        if repeated_digits:
            self.repeated_digits_in_number_message(repeated_digits)
            return False

        # Finally number is correct
        return True

    def round(self):
        """Round method.

        Handle inserting answers, taking special commands, viewing results.

        RETURN:
            'quit' - if player inserted '!quit'
            'restart' - if player inserted '!restart'
            'end' - if game ended successfully
        """
        self.initing_round()
        while True: # Round loop
            input_ = self.take_number()
            input_ = input_.strip()

            if not input_:
                self.empty_input_message()
                continue

            # Detect special input
            if len(input_) > 1:
                if re.match(input_, '!quit', flags=re.I):
                    self.ending_round()
                    return 'quit'
                if re.match(input_, '!restart', flags=re.I):
                    self.ending_round()
                    return 'restart'
            if re.match('!', input_, flags=re.I):
                self.special_input_hint_message()
                continue

            if not self.is_number_syntax_corect(input_):
                continue

            bullscows = self.comput_bullscows(input_)
            if bullscows['bulls'] == self.number_size:
                self.game_score_message()
                self.ending_round()
                return 'end'

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
            return_ = self.round()
            if return_ == 'end':
                if self.ask_if_continue_playing():
                    continue
                else:
                    return
            elif return_ == 'restart':
                pass
            else:
                return
