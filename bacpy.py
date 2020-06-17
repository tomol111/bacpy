"""BacPy - Bulls and Cows game implementation by Tomasz Olszewski"""


__version__ = '0.2'
__author__ = 'Tomasz Olszewski'


from abc import ABCMeta, abstractmethod
from collections import Counter
from dataclasses import dataclass
from math import factorial
import random
import re
import subprocess
from textwrap import dedent
from time import sleep
from typing import (ClassVar, Collection, Dict, FrozenSet, Iterable,
                    Iterator, List, Optional, Union, Tuple, Type, TypeVar)
from typing_extensions import Literal

from pandas import Series  # type: ignore

# Type variables
T = TypeVar('T')

# Constants
DEBUGING_MODE = True
DIF_INDEX_START = 1


# =========
# GameAware
# =========


class GameAware:
    """Give it's subclasses access to the 'Game' instance by 'self.game'."""
    game: ClassVar['Game']

    @classmethod
    def game_set(cls, game: 'Game') -> None:
        """Should be call at Game object initiation."""
        cls.game = game


# ============
# Difficulties
# ============


@dataclass(frozen=True)
class Difficulty:
    """Game difficulty parameters."""
    __slots__ = ('name', 'digs_set', 'digs_range', 'num_size')
    name: str
    digs_set: FrozenSet[str]
    digs_range: str
    num_size: int

    @classmethod
    def from_str(cls, string: str, sep: str = ',') -> 'Difficulty':
        """Create difficulty object from strings."""
        name, digs_set_str, digs_range, num_size_str = map(
            lambda x: x.strip(), string.split(sep))

        digs_set = frozenset(digs_set_str)
        num_size = int(num_size_str)

        return cls(name, digs_set, digs_range, num_size)

    @property
    def variance(self) -> int:
        """All possible numbers for this difficulty settings."""
        n = len(self.digs_set)
        k = self.num_size
        return round(factorial(n) / factorial(n-k))

    def __eq__(self, other: object) -> bool:
        """Compare 'variance' and 'num_size'."""
        if not isinstance(other, Difficulty):
            return NotImplemented
        return (self.variance == other.variance
                and self.num_size == other.num_size)

    def __lt__(self, other: object) -> bool:
        """Compare 'variance' and 'num_size'.

        Return True if 'variance' is less than or
        if 'variance' is equal and 'num_size' is grater than.
        """
        if not isinstance(other, Difficulty):
            return NotImplemented
        return (self.variance < other.variance
                or self.variance == other.variance
                and self.num_size > self.num_size)


class DifficultyContainer(Collection[Difficulty], Iterable[Difficulty]):
    """Keeps available difficulties.

    Uses DIF_INDEX_START to handle index."""

    DEFAULT_DIFS = [Difficulty.from_str(record) for record in (
        'easy,   123456,         1-6,    3',
        'normal, 123456789,      1-9,    4',
        'hard,   123456789abcdf, 1-9a-f, 5',
    )]

    def __init__(self) -> None:
        self._difs = Series(
            {dif.name: dif for dif in self.DEFAULT_DIFS}, dtype=object)
        self._difs.sort_values(inplace=True)

    def __iter__(self) -> Iterator[Difficulty]:
        return iter(self._difs)

    def __len__(self) -> int:
        return len(self._difs)

    def __getitem__(self, key: Union[str, int]) -> Difficulty:
        """Return Difficulty by given name or index."""
        if isinstance(key, int):
            key -= DIF_INDEX_START
        return self._difs[key]

    def __contains__(self, name: object) -> bool:
        """Return True if given name is available."""
        return name in self._difs.index

    @property
    def names(self) -> List[str]:
        """List of names."""
        return list(self._difs.index)

    def isindex(self, number: int) -> bool:
        """Return True if given number is available index."""
        return isinstance(number, int) and \
            DIF_INDEX_START <= number < len(self)+DIF_INDEX_START

    def iter_elements(
            self,
            elements: List[Literal['index', 'name', 'num_size',
                                   'digs_range', 'digs_set']],
            index_start: int = DIF_INDEX_START) -> Iterator[List[str]]:
        """Iterate through available difficulties' elements in given order."""

        for ind, dif in enumerate(self, start=index_start):
            record = []
            for element in elements:
                if hasattr(dif, element):
                    record.append(getattr(dif, element))
                elif element == 'index':
                    record.append(ind)
                else:
                    raise KeyError(f"'{element}' element can't be used")
            yield record

    def get(self, key: Union[str, int], default: Optional[T] = None) \
            -> Union[Difficulty, Optional[T]]:
        """Return difficulty for key. If key don't exist return 'default.

        Key can be 'name' or index number.
        """
        try:
            item = self[key]
        except KeyError:
            return default
        else:
            return item


# ===============
# History classes
# ===============


@dataclass(frozen=True)
class HistoryRecord:
    """Keep round step data."""
    __slots__ = ('step', 'bulls', 'cows')
    step: int
    bulls: int
    cows: int


class HistoryContainer:
    """Keep HistoryRecords."""

    def __init__(self, difficulty: Difficulty) -> None:
        self._difficulty = difficulty
        self._records = []

    def __iter__(self) -> Iterator[HistoryRecord]:
        return iter(self._records[:])

    @property
    def difficulty(self):
        return self._difficulty

    def append(self, item: HistoryRecord) -> None:
        self._records.append(item)

    def iter_elements(self, elements: List[Literal['step', 'bulls', 'cows']])\
            -> Iterator[List[int]]:
        """Iterate through available HistoryRecords' elements in given order."""
        for item in self:
            record = []
            for element in elements:
                if hasattr(item, element):
                    record.append(getattr(item, element))
                else:
                    raise KeyError(f"'{element}' element can't be used")
            yield record


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
    """Exception raised by Command.

    Error description will be shown on the interface.
    """


# ========
# CLITools
# ========


class CLITools:
    """Class with basic methods for CLI."""

    def _ask_ok(self, prompt: str, default: bool = True) -> bool:
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

    def pager(self, string: str, program: str = 'less',
              args: Optional[List[str]] = None) -> None:
        """Use pager to show text."""
        # '-C' flag prevent from showing text on bottom of the screen
        args = ['-C'] if args is None else []

        with subprocess.Popen([program, *args],
                              stdin=subprocess.PIPE) as pager:
            pager.stdin.write(str.encode(string))  # type: ignore
            pager.stdin.close()  # type: ignore
            pager.wait()


# ============
# Commands
# ============


class Command(CLITools, GameAware, metaclass=ABCMeta):
    """Command abstract class and commands manager."""

    PREFIX: ClassVar[str] = '!'

    doc: Optional[str]
    name: str
    shorthand: str

    @abstractmethod
    def execute(self, arg: str) -> None:
        """Main method."""

    @classmethod
    def __subclasshook__(cls, subclass: T) -> bool:
        return hasattr(subclass, 'execute')

    @classmethod
    def __init_subclass__(cls, **kwargs: T) -> None:
        super().__init_subclass__(**kwargs)  # type: ignore

        if not hasattr(cls, 'name'):
            cls.name = cls.__name__
        if not hasattr(cls, 'doc'):
            cls.doc = cls.__doc__


class CommandContainer(Collection[Type[Command]], Iterable[Type[Command]]):
    """Contain Command objects and allows execute them."""

    def __init__(self) -> None:
        cmdsubclasses: List[Type[Command]] = Command.__subclasses__()
        self._cmds: Dict[str, Type[Command]] = \
            {cmd.name: cmd for cmd in cmdsubclasses}
        self._shorthands_map: Dict[str, str] = \
            {cmd.shorthand: cmd.name for cmd in cmdsubclasses}

    def __iter__(self) -> Iterator[Type[Command]]:
        return iter(self._cmds.values())

    def __getitem__(self, key: str) -> Type[Command]:
        """Give Command by given name or shorthand."""
        if key in self._shorthands_map:
            return self._cmds[self._shorthands_map[key]]
        if key in self._cmds:
            return self._cmds[key]
        raise IndexError(key)

    def __len__(self) -> int:
        """Return number of Commands."""
        return len(self._cmds)

    def __contains__(self, key: object) -> bool:
        """Return True if given name or shorthand is available."""
        return key in self.names or key in self.shorthands

    @property
    def names(self) -> List[str]:
        """Return list of names."""
        return list(self._cmds)

    @property
    def shorthands(self) -> List[str]:
        """Return list of shorthands."""
        return list(self._shorthands_map)

    def get(self, key: str, default: Optional[T] = None) \
            -> Union[Type[Command], Optional[T]]:
        """Return command class for key.

        If key don't exist return 'default'.
        """
        try:
            item = self[key]
        except KeyError:
            return default
        else:
            return item

    def parse_cmd(self, input_: str) -> None:
        """Search for command and execute it."""
        input_ = input_[len(Command.PREFIX):].lstrip()
        if input_:
            name, *line = input_.split(maxsplit=1)
            if name in self:
                cmd = self[name]
                arg = line[0] if line else ''
                try:
                    cmd().execute(arg)
                except CommandError as err:
                    print(err)
                except Exception:
                    if DEBUGING_MODE:
                        raise
                    else:
                        print(f"  Unknown error while executing "
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
    shorthand = 'h'

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

    def execute(self, arg: str) -> None:
        if not arg:
            self.pager(self.GAME_HELP)
            return

        if arg == 'commands':
            self._commands_help()
            return

        if arg in self.game.commands:
            cmd = self.game.commands[arg]
            if cmd.doc is not None:
                print(cmd.doc)
            else:
                print(f"  Command {cmd} don't have documentation")
            return

        raise CommandError(f"  No help for '{arg}'")

    def _commands_help(self) -> None:
        """Run pager with all commands' doc."""
        self.pager('\n'.join([cmd.doc for cmd in self.game.commands
                              if cmd.doc is not None]))


class Quit(Command):
    """!q[uit]

    Quit the game.
    """

    name = 'quit'
    shorthand = 'q'

    def execute(self, arg: str) -> None:
        if arg:
            raise CommandError(f"  '{self.name}' command take no arguments")

        raise QuitGame


class Restart(Command):
    """!r[estart]

    Restart the round.
    """

    name = 'restart'
    shorthand = 'r'

    def execute(self, args: str) -> None:
        if args:
            raise CommandError(f"  '{self.name}' command take no arguments")

        raise RestartGame


class DifficultyCmd(Command):
    """!d[ifficulty] [{difficulty_name} | {difficulty_key} | -l]

    Change difficulty to the given one. If not given directly show
    difficulty selection.
    """

    name = 'difficulty'
    shorthand = 'd'

    def difficulties_table(self) -> None:
        """Print table with available difficulties."""
        for record in self.game.difs.iter_elements(
                ['index', 'name', 'num_size', 'digs_range']):
            print(' {:>2}) {:<8} {:^4} {:^6} '.format(*record))

    def execute(self, arg: str) -> None:
        if not arg:
            try:
                difficulty = DifficultySelection().run()
            except CancelOperation:
                return
            else:
                self.game.current_dif = difficulty
                raise RestartGame

        if arg == '-l':
            self.difficulties_table()
            return

        try:
            if arg.isdigit():
                difficulty = self.game.difs[int(arg)]
            else:
                difficulty = self.game.difs[arg]
        except (KeyError, IndexError):
            raise CommandError(f"  There is no '{arg}' difficulty")
        else:
            self.game.current_dif = difficulty
            raise RestartGame


class Clear(Command):
    """!c[lean]

    Clear screan.
    """

    name = 'clear'
    shorthand = 'c'

    def execute(self, arg: str) -> None:
        if arg:
            raise CommandError(f"  '{self.name}' command take no arguments")

        subprocess.Popen(['clear'])
        sleep(0.001)  # some time to clear the screen before printing


class History(Command):
    """!h[istory] [-c]

    Show history.
        '-c' - before showing history clear the screan
    """

    name = 'history'
    shorthand = 'hi'

    def execute(self, arg: str) -> None:
        if arg == '-c':
            self.game.commands['clear']().execute('')
        elif arg:
            raise CommandError(f"  invalid argument '{arg}'")
        print("  Step  Bulls  Cows")
        for step, bulls, cows in self.game.round.history.iter_elements(
                ['step', 'bulls', 'cows']):
            print(f"  {step:>2}:    {bulls:>2}     {cows:>2}")


# ============
# Core classes
# ============


class DifficultySelection(CLITools, GameAware):
    """Difficulty selection class."""

    def __init__(self) -> None:
        self._table = self._build_table()
        self._selection_start = \
            '------ Difficulty selection ------'
        self._selection_end = \
            '----------------------------------'

    def _build_table(self) -> str:
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
            for record in self.game.difs.iter_elements(
                ['index', 'name', 'num_size', 'digs_range'])
        )

        return '\n'.join([*top_table, *inner_rows, *bottom_table])

    def _loop(self) -> Difficulty:
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
                difficulty = self.game.difs[int(input_)]
            except (ValueError, IndexError):
                continue
            else:
                return difficulty

    def run(self) -> Difficulty:
        """Run difficulty selection."""
        print(self._selection_start)
        print(self._table)
        try:
            return self._loop()
        finally:
            print(self._selection_end)


class Round(CLITools, GameAware):
    """Round class."""

    def __init__(self, difficulty: Difficulty) -> None:
        self.history = HistoryContainer(difficulty)

        self._dif_name = difficulty.name
        self._num_size = difficulty.num_size
        self._digs_set = difficulty.digs_set
        self._digs_range = difficulty.digs_range

        self._draw_number()
        if DEBUGING_MODE:
            print(self._number)
        self._steps: Optional[int] = None

    def _draw_number(self) -> None:
        """Draw number digits from self._digs_set."""
        self._number = ''.join(
            random.sample(self._digs_set, self._num_size)
        )

    def _loop(self) -> None:
        """Round main loop."""
        self._steps = 1
        while True:
            bulls, cows = self._comput_bullscows(self._number_input())
            self.history.append(HistoryRecord(self._steps, bulls, cows))

            if bulls == self._num_size:
                self._score_output()
                return

            self._bulls_and_cows_output(bulls, cows)
            self._steps += 1

    def run(self) -> None:
        """Run round loop.

        It is responsible to call self._start_game and self._end_game.
        """

        self._start_round()
        try:
            self._loop()
        finally:
            self._end_round()

    def _comput_bullscows(self, guess: str) -> Tuple[int, int]:
        """Return bulls and cows for given input."""
        bulls, cows = 0, 0

        for i in range(self._num_size):
            if guess[i] == self._number[i]:
                bulls += 1
            elif re.search(guess[i], self._number):
                cows += 1

        return bulls, cows

    def is_number_valid(self, number: str, outputs: bool = True) -> bool:
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

    def _start_round(self) -> None:
        """Print round starting message"""
        print(dedent(f"""
            ===== Starting round =====

              Difficulty:  {self._dif_name:>9}
              Number size: {self._num_size:>9}
              Digits range:{self._digs_range:>9}
        """))

    def _end_round(self) -> None:
        """Print round ending message"""
        print('======= Round ended ======\n')

    def _wrong_chars_in_num_output(self, wrong_chars: Iterable[str],
                                   wrong_input: str) -> None:
        """Print wrong characters in number message"""
        wrong_chars = ', '.join(map(lambda x: f"'{x}'", wrong_chars))
        print(
            f'  Wrong characters: {wrong_chars}.'
            f' Correct are: "{self._digs_range}".'
        )

    def _wrong_num_len_output(self, length: int) -> None:
        """Print wrong length of number message"""
        print(f"  You entered {length} digits but {self._num_size} "
              f"is expected.")

    def _rep_digs_in_num_output(self, rep_digs: Iterable[str],
                                wrong_input: str) -> None:
        """Print repeated digits in number message"""
        rep_digs_str = ', '.join(
            map(lambda x: f"'{x}'", rep_digs)
        )
        print(f"  Number can't have repeated digits. {rep_digs_str} repeated.")

    def _number_input(self) -> str:
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

    def _bulls_and_cows_output(self, bulls: int, cows: int) -> None:
        """Print bulls and cows message"""
        print(f"  bulls: {bulls:>2}, cows: {cows:>2}")

    def _score_output(self) -> None:
        """Print score message"""
        print(f"\n *** You guessed in {self._steps} steps ***\n")


class Game(CLITools):
    """Game class."""

    def __init__(self, difficulty: Optional[Difficulty] = None) -> None:
        self.current_dif = difficulty
        GameAware.game_set(self)
        self.difs = DifficultyContainer()
        self.commands = CommandContainer()

    def _loop(self) -> None:
        """Main Game loop."""
        # Setting difficulty
        if self.current_dif is None:
            try:
                difficulty = DifficultySelection().run()
            except CancelOperation:
                return
            else:
                self.current_dif = difficulty

        while True:  # Game loop
            try:
                self.round = Round(self.current_dif)
                self.round.run()
            except RestartGame:
                continue
            except QuitGame:
                return
            finally:
                del self.round

            try:
                if self._ask_if_continue_playing():
                    continue
                else:
                    return
            except CancelOperation:
                return

    def run(self) -> None:
        """Runs game loop.

        It is responsible to call self._start_game and self._end_game.
        """

        self._start_game()
        try:
            self._loop()
        finally:
            self._end_game()

    def _start_game(self) -> None:
        """Print game starting message"""
        print(dedent("""
            ==================================
            ---------- Game started ----------
            ==================================
        """))

    def _end_game(self) -> None:
        """Print game ending message"""
        print(dedent("""
            ==================================
            ----------- Game ended -----------
            ==================================
        """))

    def _ask_if_continue_playing(self) -> bool:
        """Ask user if he want to continue playing"""
        return self._ask_ok('Do you want to continue? [Y/n]: ')


if __name__ == '__main__':
    Game().run()
