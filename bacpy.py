"""BacPy - Bulls and Cows game implementation by Tomasz Olszewski"""


__version__ = '0.2'
__author__ = 'Tomasz Olszewski'


from abc import ABCMeta, abstractmethod
from collections import Counter
from dataclasses import dataclass
import random
import re
import subprocess
import sys
from textwrap import dedent

from pandas import Series


DEBUGING_MODE = True


# =========
# GameAware
# =========


class GameAware:
    """Give it's subclasses access to the 'Game' instance by 'self.game'."""
    @staticmethod
    def game_set(game):
        """Should be runed at Game object initiation."""
        GameAware.game = game


# ============
# Difficulties
# ============


@dataclass(frozen=True)
class Difficulty:
    """Game difficulty parameters."""
    __slots__ = ('name', 'digs_set', 'digs_range', 'num_size')
    name: str
    digs_set: frozenset
    digs_range: str
    num_size: int

    @classmethod
    def from_str(cls, string, sep=','):
        """Create difficulty object from strings."""
        name, digs_set, digs_range, num_size = map(
            lambda x: x.strip(), string.split(sep))

        digs_set = frozenset(digs_set)
        num_size = int(num_size)

        return cls(name, digs_set, digs_range, num_size)


class DifficultyContainer:
    """Keeps avaiable difficulties."""

    DEFAULT_DIFS = [Difficulty.from_str(record) for record in (
        'easy,   123456,         1-6,    3',
        'normal, 123456789,      1-9,    4',
        'hard,   123456789abcdf, 1-9a-f, 5',
    )]

    def __init__(self):
        self._difs = Series(dtype=object)
        self.update(self.DEFAULT_DIFS)

    def __iter__(self):
        return iter(self._difs)

    def __len__(self):
        return len(self._difs)

    def __getitem__(self, key):
        return self._difs[key]

    def __contains__(self, name):
        """Return True if given name is available."""
        return name in self._difs.index

    def names(self):
        """Return list of names."""
        return list(self._difs.index)

    def isindex(self, number):
        """Return True if given number is in index range."""
        return 0 <= number < len(self)

    def update(self, difs):
        """Update available difficulties."""
        for dif in difs:
            self._difs[dif.name] = dif

    def iter_elements(self, elements, index_start=0):
        """Iterate through available difficulties' elements in given order.

        Valid elements:
            * 'index'
            * 'name'
            * 'num_size'
            * 'digs_range'
            * 'digs_set'
        """
        for ind, dif in enumerate(self, start=index_start):
            record = []
            for element in elements:
                if hasattr(dif, element):
                    record.append(getattr(dif, element))
                elif element == 'index':
                    record.append(ind)
                else:
                    raise KeyError(f"{element} element can't be used")
            yield record

    def get(self, key, default=None):
        """Return difficulty for key. If key don't exist return 'default.

        Key can be 'name' or index number.
        """
        return self._difs.get(key, default)


# ======
# Events
# ======


class GameEvent(Exception):
    """Base game event class."""


class QuitGame(GameEvent):
    """Quit game event."""


class RestartGame(GameEvent):
    """Restart game event."""


class CancelOperation(GameEvent):
    """Operation canceled event."""


class CommandError(GameEvent):
    """Exception raised by command.

    Error description will be shown on the interface.
    """


# ========
# CLITools
# ========


class CLITools:
    """Class with basic methods for CLI."""

    def _ask_ok(self, prompt, default=True):
        """Yes-No input."""
        while True:
            try:
                input_ = re.escape(input(prompt).strip())
            except EOFError:
                print()  # Print lost new line character
                raise CancelOperation
            except KeyboardInterrupt:
                print()  # Print lost new line character
                continue

            if not input_:
                return default
            if re.match(input_, 'yes', flags=re.I):
                return True
            if re.match(input_, 'no', flags=re.I):
                return False

    def pager(self, string, program='less', args=None):
        """Use pager to show text."""
        if args is None:
            args = ['-C']  # Prevent from showing text on bottom of the screen
        elif args is False:
            args = []
        with subprocess.Popen(
                [program, *args],
                stdin=subprocess.PIPE, stdout=sys.stdout) as pager:
            pager.stdin.write(str.encode(string))
            pager.stdin.close()
            pager.wait()


# ============
# Commands
# ============


class Command(CLITools, GameAware, metaclass=ABCMeta):
    """Command abstract class and commands manager."""

    PREFIX = '!'

    shortcut = None
    split_args = True

    @abstractmethod
    def execute(self, args):
        """Main method."""

    @classmethod
    def __subclasshook__(cls, subclass):
        return hasattr(subclass, 'execute')

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        if not hasattr(cls, 'name'):
            cls.name = cls.__name__
        if not hasattr(cls, 'doc'):
            cls.doc = cls.__doc__


class CommandContainer:
    """Contain Command objects and allows execute them."""

    def __init__(self):
        self._cmds = {}
        self._shortcuts_map = {}

        self.update(Command.__subclasses__())

    def __iter__(self):
        return iter(self._cmds.values())

    def names(self):
        """Return list of names."""
        return list(self._cmds.keys())

    def update(self, cmds):
        """Update available commands."""
        self._cmds.update({cmd.name: cmd for cmd in cmds})
        self._shortcuts_map.update(
            {cmd.shortcut: cmd.name for cmd in cmds})

    def get(self, name, default=None, shortcuts=True):
        """Return command class for key. If key don't exist return 'default'.  """
        if shortcuts and name in self._shortcuts_map:
            return self._cmds[self._shortcuts_map]
        return self._cmds.get(name, default)

    def parse_cmd(self, input_):
        """Search for command and execute it."""
        command = input_[len(Command.PREFIX):].lstrip()
        if command:
            name, *line = command.split(maxsplit=1)
            if line:
                args = line[0]
            else:
                args = ''

            for cmd in self:
                if name in (cmd.shortcut, cmd.name):
                    if cmd.split_args:
                        args = args.split()
                    try:
                        cmd().execute(args)
                    except CommandError as err:
                        print(err)
                    except Exception:
                        if DEBUGING_MODE:
                            raise
                        else:
                            print(f" Unnown error while executing "
                                  f"{cmd.name} command")
                    return
        print(
            "  Type '!help' to show game help or '!help commands' ",
            "  to show help about available commands",
            sep='\n',
        )


class Help(Command):
    """!h[elp] [{subject}]

    Show help about {subject}. When {subject} is not parsed show game help.
    """

    name = 'help'
    shortcut = 'h'
    split_args = False

    GAME_HELP = dedent("""
        # HELP

        BacPy is "Bulls and Cows" game implementation.

        Rules are:
           * You have to guess number of witch digits do not repeat.
           * Enter your guess and program will return numbers of
             bulls (amount of digits that are correct and have
             correct position) and cows (amount of correct digits
             but with wrong position).
           * Try to find correct number with fewest amount of
             attempts.

        Special commands:
            You can type '!h commands' to show available commands.
    """)

    def execute(self, arg):
        if not arg:
            self.pager(self.GAME_HELP)
        elif arg == 'commands':
            self._commands_help()
        elif arg in self.game.commands.names():
            print(self.game.commands.get(arg).doc)
            return
        else:
            raise CommandError(f"  No help for '{arg}'")

    def _commands_help(self):
        """Run pager with all commands' doc."""
        self.pager('\n'.join([cmd.doc for cmd in self.game.commands]))


class Quit(Command):
    """!q[uit]

    Quit the game.
    """

    name = 'quit'
    shortcut = 'q'

    def execute(self, args):
        if args:
            raise CommandError(f"  '{self.name}' command take no arguments")

        raise QuitGame


class Restart(Command):
    """!r[estart]

    Restart the round.
    """

    name = 'restart'
    shortcut = 'r'

    def execute(self, args):
        if args:
            raise CommandError(f"  '{self.name}' command take no arguments")

        raise RestartGame


class DifficultyCmd(Command):
    """!d[ifficulty] [{difficulty_name} | -l]

    Change difficulty to the given one. If not given directly show
    difficulty selection.
    """

    name = 'difficulty'
    shortcut = 'd'
    split_args = False

    def difficulties_table(self):
        """Print table with available difficulties."""
        for record in self.game.difficulties.iter_elements(
                ['index', 'name', 'num_size', 'digs_range'], index_start=1):
            print(' {:>2}) {:<8} {:^4} {:^6} '.format(*record))

    def execute(self, arg):
        if arg:
            if arg == '-l':
                self.difficulties_table()
            elif arg in self.game.difficulties.names():
                self.game.set_difficulty(arg)
                raise RestartGame
            elif arg.isdigit() and self.game.difficulties.isindex(int(arg)-1):
                self.game.set_difficulty(int(arg)-1)
                raise RestartGame
            else:
                raise CommandError(f"  There is no '{arg}' difficulty")
        else:
            try:
                DifficultySelection().run()
            except CancelOperation:
                return
            else:
                raise RestartGame


# ============
# Core classes
# ============


class DifficultySelection(CLITools, GameAware):
    """Difficulty selection class."""

    def __init__(self):
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
            '  {:>2})   {:<11} {:^4}  {:^6} '
        bottom_table = ('',)

        inner_rows = (
            inner_row_template.format(*record)
            for record in self.game.difficulties.iter_elements(
                ['index', 'name', 'num_size', 'digs_range'], index_start=1)
        )

        return '\n'.join([*top_table, *inner_rows, *bottom_table])

    def _loop(self):
        """Taking from user difficulty option."""
        while True:
            try:
                input_ = input('Enter key: ').strip()
            except EOFError:
                print()  # Print lost new line character
                raise CancelOperation
            except KeyboardInterrupt:
                print()  # Print lost new line character
                continue

            try:
                index = int(input_) - 1
                if index in self.game.difficulties.index():
                    difficulty = self.game.difficulties.get(index)
                else:
                    continue
            except (KeyError, ValueError):
                continue

            if difficulty:
                break

        self.game.set_difficulty(difficulty)

    def run(self):
        """Run difficulty selection."""
        print(self._selection_start)
        print(self._table)
        try:
            return self._loop()
        finally:
            print(self._selection_end)


class Round(CLITools, GameAware):
    """Round class."""

    def __init__(self, difficulty):
        self._difficulty = difficulty.name
        self._num_size = difficulty.num_size
        self._digs_set = difficulty.digs_set
        self._digs_range = difficulty.digs_range

        self._draw_number()
        if DEBUGING_MODE:
            print(self._number)
        self._steps = None

    def set_difficulty(self, difficulty):
        """Setting difficulty."""

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
        print(dedent(f"""
            ===== Starting round =====

              Difficulty:  {self._difficulty:>9}
              Number size: {self._num_size:>9}
              Digits range:{self._digs_range:>9}
        """))

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
        print(f"  You entered {length} digits but {self._num_size} "
              f"is expected.")

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
                print()  # Print lost new line character
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
                print()  # Print lost new line character
                continue

            if not input_:
                continue

            if input_.startswith(Command.PREFIX):
                self.game.commands.parse_cmd(input_)
                continue

            if not self.is_number_valid(input_):
                continue

            return input_

    def _bulls_and_cows_output(self, bulls, cows):
        """Print bulls and cows message"""
        print(f"  bulls: {bulls:>2}, cows: {cows:>2}")

    def _score_output(self):
        """Print score message"""
        print(f"\n *** You guessed in {self._steps} steps ***\n")


class Game(CLITools):
    """Game class."""

    def __init__(self, difficulty=None):
        GameAware.game_set(self)
        self.difficulties = DifficultyContainer()
        self.commands = CommandContainer()

        if difficulty is None:
            self.current_difficulty = None
        else:
            self.set_difficulty(difficulty)

    def set_difficulty(self, difficulty):
        if difficulty is None:
            self.current_difficulty = None
        elif isinstance(difficulty, Difficulty):
            self.current_difficulty = difficulty
        elif isinstance(difficulty, (str, int)):
            self.current_difficulty = self.difficulties.get(difficulty)
        else:
            raise TypeError(f"wrong 'difficulty' type ({type(difficulty)})")

    def _loop(self):
        """Main Game loop."""
        # Setting difficulty
        if self.current_difficulty is None:
            try:
                DifficultySelection().run()
            except CancelOperation:
                return

        while True:  # Game loop
            try:
                Round(self.current_difficulty).run()
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
        print(dedent("""
            ==================================
            ---------- Game started ----------
            ==================================
        """))

    def _end_game(self):
        """Print game ending message"""
        print(dedent("""
            ==================================
            ----------- Game ended -----------
            ==================================
        """))

    def _ask_if_continue_playing(self):
        """Ask user if he want to continue playing"""
        return self._ask_ok('Do you want to continue? [Y/n]: ')


if __name__ == '__main__':
    Game().run()
