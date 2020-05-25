"""BacPy - Bulls and Cows game implementation by Tomasz Olszewski"""


__version__ = '0.2'
__author__ = 'Tomasz Olszewski'


from collections import Counter
from dataclasses import dataclass
import subprocess
import sys
import random
import re


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
# Difficulties
# ============


@dataclass(frozen=True)
class Difficulty:
    """Game difficulty parameters."""

    name: str
    digs_set: frozenset
    digs_range: str
    num_size: int

    @classmethod
    def from_str(cls, string, sep=','):
        """Create difficulty object from strings."""
        name, digs_set, digs_range, num_size = list(
            map(lambda x: x.strip(), string.split(sep)))

        digs_set = frozenset(digs_set)
        num_size = int(num_size)

        return cls(name, digs_set, digs_range, num_size)


DIFFICULTIES = [Difficulty.from_str(record) for record in (
    'easy,   123456,         1-6,    3',
    'normal, 123456789,      1-9,    4',
    'hard,   123456789abcdf, 1-9a-f, 5',
)]


# ============
# Core classes
# ============


class CLITools:
    """Class with basic methods for CLI."""

    def _ask_ok(self, prompt, default=True):
        """Yes-No input."""
        while True:
            try:
                input_ = re.escape(input(prompt).strip())
            except EOFError:
                print() # Print lost new line character
                raise CancelOperation
            except KeyboardInterrupt:
                print() # Print lost new line character
                continue

            if not input_:
                return default
            elif re.match(input_, 'yes', flags=re.I):
                return True
            elif re.match(input_, 'no', flags=re.I):
                return False

    def pager(self, string, program='less', args=None):
        """Use pager to show text."""
        if args is None:
            args=[]
        with subprocess.Popen([program, *args],
                stdin=subprocess.PIPE, stdout=sys.stdout) as pager:
            pager.stdin.write(str.encode(string))
            pager.stdin.close()
            pager.wait()


class DifficultySelection(CLITools):
    """Difficulty selection class"""

    def __init__(self):
        # Make class attributes
        self._options_dict = dict(enumerate(DIFFICULTIES, start=1))
        self._table = self._build_table()
        self._selection_start = \
            '------ Difficulty selection ------'
        self._selection_end = \
            '----------------------------------'
    def _build_table(self):
        """Prepare table"""

        top_table = (
            '',
            '  key  difficulty   size  digits  ',
        )
        inner_row_template = \
            ' {key:>2})    {difficulty:<11} {size:^4}  {digits:^6} '
        bottom_table = ('',)

        inner_rows = (
            inner_row_template.format(
                key=key,
                difficulty=difficulty.name,
                size=difficulty.num_size,
                digits=difficulty.digs_range
            ) for key, difficulty in self._options_dict.items()
        )

        return '\n'.join([*top_table, *inner_rows, *bottom_table])

    def _loop(self):
        """Taking from user difficulty option."""
        while True:
            try:
                input_ = input('Enter key: ').strip()
            except EOFError:
                print() # Print lost new line character
                raise CancelOperation
            except KeyboardInterrupt:
                print() # Print lost new line character
                continue

            if (not input_.isdigit()
                    or int(input_) not in self._options_dict):
                continue
            else:
                break

        return self._options_dict[int(input_)]

    def run(self):
        """Run difficulty selection."""
        print(self._selection_start)
        print(self._table)
        try:
            return self._loop()
        finally:
            print(self._selection_end)


class Round(CLITools):
    """Round class."""

    def __init__(self, difficulty):
        self.set_difficulty(difficulty)
        self._draw_number()
        print(self._number) # TESTING PRINT
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
        """Run round loop.

        It is responsible to call self._start_game and self._end_game.
        """

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

    def _start_round(self):
        """Print round starting message"""
        print('\n'.join([
            '',
            '===== Starting round =====',
            '',
           f'  Difficulty:  {self._difficulty:>9}',
           f'  Number size: {self._num_size:>9}',
           f'  Digits range:{self._digs_range:>9}',
            '',
        ]))

    def _end_round(self):
        """Print round ending message"""
        print('======= Round ended ======\n')


    def _wrong_chars_in_num_output(self, wrong_chars, wrong_input):
        """Print wrong characters in number message"""
        wrong_chars = ', '.join(map(lambda x: f"'{x}'", wrong_chars))
        print(
            f'  Wrong characters: {wrong_chars}.'
            f' Correct are: "{self._digs_range}".'
        )

    def _wrong_num_len_output(self, length):
        """Print wrong length of number message"""
        print(f"  You entered {length} digits but {self._num_size} is expected.")

    def _rep_digs_in_num_output(self, rep_digs, wrong_input):
        """Print repeated digits in number message"""
        rep_digs_str = ', '.join(
            map(lambda x: f"'{x}'", rep_digs)
        )
        print(f"  Number can't have repeated digits. {rep_digs_str} repeated.")

    def _number_input(self):
        """Take number from user.

        Supports special input."""
        while True:
            try:
                input_ = input(f"[{self._steps}] ").strip()
            except EOFError:
                print() # Print lost new line character
                try:
                    if self._ask_ok(
                            'Do you really want to quit? [Y/n]: '):
                        raise QuitGame
                    else:
                        continue
                except CancelOperation:
                    raise QuitGame
                continue
            except KeyboardInterrupt:
                print() # Print lost new line character
                continue

            if not input_:
                continue

            # Detect special input
            if input_.startswith('!'):
                if len(input_) > 1:
                    command = input_[1:]
                    if re.match(command, 'quit'):
                        raise QuitGame
                    elif re.match(command, 'restart'):
                        raise RestartGame
                    elif re.match(command, 'help'):
                        self.show_help()
                        continue
                    else:
                        self.special_input_hint_output()
                        continue
                else:
                    self.special_input_hint_output()
                    continue

            input_ = re.sub(r'\s+', '', input_)
            if not self.is_number_valid(input_):
                continue

            return input_

    def _bulls_and_cows_output(self, bulls, cows):
        """Print bulls and cows message"""
        print(f"  bulls: {bulls:>2}, cows: {cows:>2}")

    def _score_output(self):
        """Print score message"""
        print(f"\n *** You guessed in {self._steps} steps ***\n")

    def special_input_hint_output(self):
        """Print hint for special inputs message"""
        print('\n'.join([
            '  !q[uit]    - quit game',
            '  !r[estart] - restart game'
        ]))

    def show_help(self):
        """Show message about game and rules."""
        self.pager('\n'.join([
            '# HELP ',
            '',
            'BacPy is "Bulls and Cows" game implementation.',
            '',
            'Rules are:',
            '   * You have to guess number of witch digits do not repeat.',
            '   * Enter your guess and program will return numbers of',
            '     bulls (amount of digits that are correct and have',
            '     correct position) and cows (amount of correct digits',
            '     but with wrong position).',
            '   * Try to find correct number with fewest amount of',
            '     attempts.']),
            args=['-C'] # Prevent from showing text on bottom of the screen
        )


class Game(CLITools):
    """Game class."""

    def __init__(self, difficulty=None):
        self._difficulty = difficulty

    def _loop(self):
        """Main Game loop."""
        # Setting difficyulty
        if self._difficulty is None:
            try:
                self._difficulty = \
                    DifficultySelection().run()
            except CancelOperation:
                return

        while True: # Game loop
            try:
                Round(self._difficulty).run()
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

    def _start_game(self):
        """Print game starting message"""
        print('\n'.join([
            '==================================',
            '---------- Game started ----------',
            '==================================',
            '',
        ]))

    def _end_game(self):
        """Print game ending message"""
        print('\n'.join([
            '==================================',
            '----------- Game ended -----------',
            '==================================',
        ]))

    def _ask_if_continue_playing(self):
        """Ask user if he want to continue playing"""
        return self._ask_ok('Do you want to continue? [Y/n]: ')


if __name__ == '__main__':
    Game().run()
