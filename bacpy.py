"""BacPy - Bulls and Cows game implementation by Tomasz Olszewski"""


__version__ = '0.2'
__author__ = 'Tomasz Olszewski'


from abc import ABCMeta, abstractmethod
from collections import Counter
from dataclasses import dataclass
from math import factorial
import os
import random
import subprocess
from textwrap import dedent
from typing import (ClassVar, Collection, Dict, FrozenSet, Iterable,
                    Iterator, List, Optional, Union, Tuple, Type, TypeVar)
from weakref import ref

import pandas as pd  # type: ignore
from prompt_toolkit import PromptSession  # type: ignore
from prompt_toolkit.document import Document  # type: ignore
from prompt_toolkit.shortcuts import clear, prompt  # type: ignore
from prompt_toolkit.validation import (  # type: ignore
        Validator, ValidationError)
from tabulate import tabulate


# Type variables
T = TypeVar('T')

# Constants
DEBUGING_MODE = True


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
        return factorial(n) // factorial(n-k)

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

    Uses DIF_INDEX_START to handle index.
    """

    DEFAULT_DIFS = [Difficulty.from_str(record) for record in (
        'easy,   123456,         1-6,    3',
        'normal, 123456789,      1-9,    4',
        'hard,   123456789abcdf, 1-9a-f, 5',
    )]
    DIF_INDEX_START = 1

    def __init__(self) -> None:
        self._difs = pd.Series(
            {dif.name: dif for dif in self.DEFAULT_DIFS}, dtype=object)
        self._difs.sort_values(inplace=True)

    def __iter__(self) -> Iterator[Difficulty]:
        return iter(self._difs)

    def __len__(self) -> int:
        return len(self._difs)

    def __getitem__(self, key: Union[str, int]) -> Difficulty:
        """Return Difficulty by given name or index."""
        if isinstance(key, int):
            key -= self.DIF_INDEX_START
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
            self.DIF_INDEX_START <= number < len(self)+self.DIF_INDEX_START

    def table(self) -> pd.DataFrame:
        """pd.DataFrame containing difficulties` 'name', 'num_size'
        and 'digs_range'."""
        dt = pd.DataFrame(columns=['name', 'num_size', 'digs_range'],
                          index=pd.RangeIndex(
                              self.DIF_INDEX_START,
                              len(self)+self.DIF_INDEX_START))

        for index, dif in enumerate(self, start=self.DIF_INDEX_START):
            for element in dt:
                dt.loc[index, element] = getattr(dif, element)

        return dt

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


# ================
# HistoryContainer
# ================


class HistoryContainer:
    """Keep HistoryRecords."""

    def __init__(self) -> None:
        self._hist = pd.DataFrame(columns=['number', 'bulls', 'cows'],
                                  index=pd.Index([], name='step'))

    def __iter__(self) -> Iterator[Tuple[int, pd.Series]]:
        return self._hist.iterrows()

    def __len__(self) -> int:
        return len(self._hist)

    def append(self, number: str, bulls: int, cows: int) -> None:
        self._hist.loc[len(self)+1] = number, bulls, cows

    def table(self):
        return self._hist[:]


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


def ask_ok(prompt_message: str, default: bool = True) -> bool:
    """Yes-No input."""
    while True:
        try:
            input_ = prompt(prompt_message).strip().lower()
        except EOFError:
            raise CancelOperation
        except KeyboardInterrupt:
            continue

        if not input_ and default is not None:
            return default
        if 'yes'.startswith(input_):
            return True
        if 'no'.startswith(input_):
            return False


def pager(text: str) -> None:
    """Use pager to show text."""
    # '-C' flag prevent from showing text on bottom of the screen
    subprocess.run(['less', '-C'], input=str.encode(text))


# ========
# Commands
# ========


class Command(metaclass=ABCMeta):
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
            pager(self.GAME_HELP)
            return

        if arg == 'commands':
            self._commands_help()
            return

        commands = get_game().commands
        if arg in commands:
            cmd = commands[arg]
            if cmd.doc is not None:
                print(cmd.doc)
            else:
                print(f"  Command {cmd} don't have documentation")
            return

        raise CommandError(f"  No help for '{arg}'")

    def _commands_help(self) -> None:
        """Run pager with all commands' doc."""
        pager('\n'.join([cmd.doc for cmd in get_game().commands
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

    def execute(self, arg: str) -> None:
        game = get_game()
        if not arg:
            try:
                difficulty = DifficultySelection().run()
            except CancelOperation:
                return
            else:
                game.current_dif = difficulty
                raise RestartGame

        if arg == '-l':
            print(tabulate(game.difs.table(),
                           headers=('Key', 'Difficulty', 'Size', 'Digits'),
                           tablefmt='plain'))
            return

        try:
            difficulty = game.difs[int(arg) if arg.isdigit() else arg]
        except (KeyError, IndexError):
            raise CommandError(f"  There is no '{arg}' difficulty")
        else:
            game.current_dif = difficulty
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

        if os.name in ('nt', 'dos'):
            subprocess.call('cls')
        elif os.name in ('linux', 'osx', 'posix'):
            subprocess.call('clear')
        else:
            clear()


class History(Command):
    """!hi[story] [-c]

    Show history.
        '-c' - before showing history clear the screan
    """

    name = 'history'
    shorthand = 'hi'

    def execute(self, arg: str) -> None:
        game = get_game()
        if arg == '-c':
            game.commands['clear']().execute('')
        elif arg:
            raise CommandError(f"  invalid argument '{arg}'")
        print(tabulate(game.round.history.table(),
                       headers=('Number', 'Bulls', 'Cows'),
                       colalign=('center', 'center', 'center'),
                       showindex=False,
                       tablefmt='plain'))


# ============
# Core classes
# ============


class DifficultySelection:
    """Difficulty selection class."""

    def __init__(self) -> None:
        self.validator = Validator.from_callable(self.validator_func,
                                                 error_message='Invalid key',
                                                 move_cursor_to_end=True)

    def table(self):
        return tabulate(get_game().difs.table(),
                        headers=('Key', 'Difficulty', 'Size', 'Digits'),
                        colalign=('right', 'left', 'center', 'center'))

    def validator_func(self, text: str) -> bool:
        try:
            return get_game().difs.isindex(int(text))
        except ValueError:
            return False

    def run(self) -> Difficulty:
        """Run difficulty selection."""
        table = self.table()

        # Compute table width
        fnlp = table.find('\n')
        width = table.find('\n', fnlp+1) - fnlp - 1

        print(' Difficulty selection '.center(width, '='))
        print('\n', table, '\n', sep='')
        try:
            while True:
                try:
                    input_ = prompt('Enter key: ',
                                    validator=self.validator,
                                    validate_while_typing=False).strip()
                except EOFError:
                    raise CancelOperation
                except KeyboardInterrupt:
                    continue

                try:
                    difficulty = get_game().difs[int(input_)]
                except (ValueError, IndexError):
                    continue
                else:
                    return difficulty
        finally:
            print(''.center(width, '='))


class RoundValidator(Validator):

    def validate(self, document: Document) -> None:
        input_: str = document.text.strip()

        difficulty = get_game().current_dif
        digs_set = difficulty.digs_set
        num_size = difficulty.num_size

        if not input_.startswith(Command.PREFIX):
            # Check if number have wrong characters
            wrong_chars = set(input_) - digs_set
            if wrong_chars:
                raise ValidationError(
                    message="Wrong characters: %s" %
                            ', '.join(map(lambda x: f"'{x}'", wrong_chars)),
                    cursor_position=max(input_.rfind(dig)
                                        for dig in wrong_chars) + 1
                )

            # Check length
            if len(input_) != num_size:
                raise ValidationError(
                    message=f"Digit must have {num_size} digits",
                    cursor_position=float('inf')
                )

            # Check that digits don't repeat
            digits = Counter(input_)
            rep_digs = {i for i, n in digits.items() if n > 1}
            if rep_digs:
                raise ValidationError(
                    message="Number can't have repeated digits. %s repeated." %
                            ', '.join(map(lambda x: f"'{x}'", rep_digs)),
                    cursor_position=max(input_.rfind(dig)
                                        for dig in rep_digs) + 1
                )


class Round:
    """Round class."""

    ROUND_START = '\n===== Round started ======\n'
    ROUND_END = '\n======= Round ended ======\n'

    def __init__(self) -> None:
        self.history = HistoryContainer()

        self._draw_number()
        if DEBUGING_MODE:
            print(self._number)

    def _draw_number(self) -> None:
        """Draw number digits from self.dif.digs_set."""
        self._number = ''.join(
            random.sample(self.dif.digs_set, self.dif.num_size)
        )

    @property
    def steps(self) -> int:
        return len(self.history)

    @property
    def dif(self) -> Difficulty:
        return get_game().current_dif

    @property
    def toolbar(self):
        return (f" Difficulty: {self.dif.name}  |  "
                f"Size: {self.dif.num_size}  |  "
                f"Digits: {self.dif.digs_range}")

    def run(self) -> None:
        """Run round loop."""
        print(self.ROUND_START)
        try:
            self.ps = PromptSession(bottom_toolbar=self.toolbar,
                                    validator=RoundValidator(),
                                    validate_while_typing=False)
            while True:
                number = self._number_input()
                bulls, cows = self.comput_bullscows(number)
                self.history.append(number, bulls, cows)

                if bulls == self.dif.num_size:
                    print(f"\n *** You guessed in {self.steps} steps ***")
                    return

                print(f"  bulls: {bulls:>2}, cows: {cows:>2}")
        finally:
            print(self.ROUND_END)

    def comput_bullscows(self, guess: str) -> Tuple[int, int]:
        """Return bulls and cows for given input."""
        bulls, cows = 0, 0

        for i in range(self.dif.num_size):
            if guess[i] == self._number[i]:
                bulls += 1
            elif guess[i] in self._number:
                cows += 1

        return bulls, cows

    def _number_input(self) -> str:
        """Take number from user.

        Supports special input."""
        while True:
            try:
                input_ = self.ps.prompt(f"[{self.steps+1}] ").strip()
            except EOFError:
                try:
                    if ask_ok('Do you really want to quit? [Y/n]: '):
                        raise QuitGame
                    else:
                        continue
                except CancelOperation:
                    raise QuitGame
                continue
            except KeyboardInterrupt:
                continue

            if not input_:
                continue

            if input_.startswith(Command.PREFIX):
                get_game().commands.parse_cmd(input_)
                continue

            return input_


class Game:
    """Game class."""

    GAME_START = dedent("""
        ==================================
        ---------- Game started ----------
        ==================================
    """)

    GAME_END = dedent("""
        ==================================
        ----------- Game ended -----------
        ==================================
    """)

    instance: ClassVar[Callable[[], Optional['Game']] = lambda: None

    def __new__(cls):
        if not hasattr(cls, 'isntance') or not cls.instance():
            instance = super(Game, cls).__new__(cls)
            cls.instance = ref(instance)
        else:
            raise TypeError(
                f"Can't create more than 1 instance of '{cls.__name__}' class")
        return instance

    def __init__(self) -> None:
        self.difs = DifficultyContainer()
        self.commands = CommandContainer()

        self.round: Round
        self.current_dif: Difficulty

    def run(self) -> None:
        """Runs game loop."""

        print(self.GAME_START)
        try:
            try:
                difficulty = DifficultySelection().run()
            except CancelOperation:
                return
            else:
                self.current_dif = difficulty

            while True:  # Game loop
                try:
                    self.round = Round()
                    self.round.run()
                except RestartGame:
                    continue
                except QuitGame:
                    return
                finally:
                    del self.round

                try:
                    if ask_ok('Do you want to continue? [Y/n]: '):
                        continue
                    else:
                        return
                except CancelOperation:
                    return
        finally:
            print(self.GAME_END)


def get_game() -> Game:
    ret = Game.instance()
    assert ret is not None, "'get_game' called before instantiate 'Game' class"
    return ret


if __name__ == '__main__':
    Game().run()
