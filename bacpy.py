from collections import Counter, deque
import contextlib
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from operator import attrgetter, itemgetter
import os
from pathlib import Path
import random
import shlex
import subprocess
import sys
from typing import (
    Callable,
    ClassVar,
    Collection,
    Container,
    Dict,
    FrozenSet,
    Iterable,
    Iterator,
    KeysView,
    List,
    NamedTuple,
    NoReturn,
    Optional,
    overload,
    Union,
    Tuple,
    TypeVar,
)

import pandas as pd
from prompt_toolkit import PromptSession
from prompt_toolkit.document import Document
from prompt_toolkit.shortcuts import clear, prompt
from prompt_toolkit.validation import Validator, ValidationError
from tabulate import tabulate

if sys.version_info >= (3, 8):
    import importlib.metadata as importlib_metadata
else:
    try:
        import importlib_metadata
    except ModuleNotFoundError:
        importlib_metadata = None


VERSION_STR = " BacPy "
if importlib_metadata:
    VERSION_STR += f"v{importlib_metadata.version('bacpy')} "


# Type variables
T = TypeVar('T')

# Constants
RANKINGS_DIR = Path('.rankings')
IDX_START = 1
RANKING_SIZE = 10

GAME_HELP = """
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
"""


# ============
# Difficulties
# ============


DIGITS_RANGE = '123456789abcdef'


@dataclass(order=True, frozen=True)
class Difficulty:

    num_size: int
    digs_num: int
    name: str = field(default='', compare=False)

    @property
    def digs_set(self) -> FrozenSet[str]:
        return frozenset(DIGITS_RANGE[:self.digs_num])

    @property
    def digs_range(self) -> str:
        if 3 <= self.digs_num <= 9:
            return f'1-{self.digs_num}'
        if self.digs_num == 10:
            return '1-9,a'
        if 11 <= self.digs_num <= 15:
            return f'1-9,a-{DIGITS_RANGE[self.digs_num-1]}'
        raise AttributeError


class DifficultyContainer:
    """Keeps available difficulties."""

    def __init__(self) -> None:
        self._data = [
            Difficulty(*dif)
            for dif in [
                (3, 6, 'easy'),
                (4, 9, 'normal'),
                (5, 15, 'hard'),
            ]
        ]

        self._mapping = {dif.name: dif for dif in self._data if dif.name}
        self._indexes = range(IDX_START, len(self) + IDX_START)

    def __iter__(self) -> Iterator[Difficulty]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __getitem__(self, key: Union[str, int]) -> Difficulty:
        """Return Difficulty by given name or index."""
        if isinstance(key, int):
            return self._data[self.indexes.index(key)]
        if isinstance(key, str):
            return self._mapping[key]
        raise TypeError(
            f"Given key have wrong type ({type(key)}). "
            "'str' or 'int' needed."
        )

    @property
    def names(self) -> KeysView[str]:
        return self._mapping.keys()

    @property
    def indexes(self) -> range:
        return self._indexes


# =======
# History
# =======


class HistRecord(NamedTuple):
    """
    History record of passed number and the corresponding bulls and cows.
    """
    number: str
    bulls: int
    cows: int


class History:
    """Stores `HistRecord`s."""

    def __init__(self) -> None:
        self._data: deque = deque()

    def add_record(self, number: str, bulls: int, cows: int) -> None:
        """Create `HistRecord` from passed data and store it."""
        self._data.append(HistRecord(number, bulls, cows))

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[HistRecord]:
        return iter(self._data)


# ======
# Events
# ======


class GameEvent(Exception):
    """Base game event class."""


class QuitGame(GameEvent):
    """Quit game event."""


class StopPlaying(GameEvent):
    """Stop playing event."""


class RestartGame(GameEvent):
    """Restart game event."""
    def __init__(self, difficulty: 'Difficulty' = None):
        self.difficulty = difficulty


class CancelOperation(GameEvent):
    """Operation canceled event."""


class CommandError(GameEvent):
    """Exception raised by Command.

    Error description will be shown on the interface.
    """


# =========
# CLI tools
# =========


class cli_window(contextlib.ContextDecorator):

    def __init__(
            self, header: str,
            fillchar: str = '=',
            wing_size: int = 5,
    ) -> None:
        self.header = header
        self.fillchar = fillchar
        self.wing_size = wing_size
        self.width = len(header) + 2 * (wing_size + 1)  # +1 is for space

    def __enter__(self):
        wing = self.fillchar * self.wing_size
        print(f'{wing} {self.header} {wing}')
        return self

    def __exit__(self, *exc):
        print(self.fillchar * self.width)
        return False


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
    subprocess.run(['less', '-C'], input=text.encode())


def show_ranking(ranking: pd.DataFrame) -> None:
    ranking = (
        ranking
        [['score', 'player']]
        .astype({'score': str})
        .reset_index(drop=True)
        .join(
            pd.Series(range(1, RANKING_SIZE + 1), name='pos.'),
            how='outer',
        )
        .set_index('pos.')
        .fillna('-')
    )

    pager(tabulate(
        ranking,
        headers='keys',
        colalign=('left', 'center', 'left'),
    ))


# ========
# Commands
# ========


class Command:
    """Command abstract class and commands manager."""

    PREFIX: ClassVar[str] = '!'
    instances: ClassVar[List['Command']] = []

    doc: Optional[str]
    name: str
    shorthand: str

    def __init__(self, cmdfunc: Callable[..., None], **kwargs: T) -> None:
        self.instances.append(self)
        self._cmdfunc = cmdfunc
        for attrname, variable in kwargs.items():
            setattr(self, attrname, variable)
        if not hasattr(self, 'name'):
            self.name = cmdfunc.__name__
        if not hasattr(self, 'doc'):
            self.doc = cmdfunc.__doc__

    def __call__(self, *args: str) -> None:
        self._cmdfunc(*args)

    @classmethod
    def add(cls, **kwargs: T) -> Callable[[Callable[..., None]], 'Command']:
        def decorator(cmdfunc):
            return cls(cmdfunc, **kwargs)
        return decorator


class CommandContainer(Collection[Command], Iterable[Command]):
    """Contain Command objects and allows execute them."""

    def __init__(self) -> None:
        self._cmds: Dict[str, Command] = {
            cmd.name: cmd for cmd in Command.instances
        }
        self._shorthands_map: Dict[str, str] = {
            cmd.shorthand: cmd.name for cmd in Command.instances
        }

    def __iter__(self) -> Iterator[Command]:
        return iter(self._cmds.values())

    def __getitem__(self, key: str) -> Command:
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

    def get(
            self,
            key: str,
            default: Optional[T] = None,
    ) -> Union[Command, Optional[T]]:
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
        input_ = input_[len(Command.PREFIX):]
        if input_:
            name, *args = shlex.split(input_)
            if name in self:
                try:
                    self[name](*args)
                except (CommandError, TypeError) as err:
                    print(err)
                return
        print(
            "  Type '!help' to show game help or '!help commands' ",
            "  to show help about available commands",
            sep='\n',
        )


@Command.add(name='help', shorthand='h')
def help_cmd(arg: str = '') -> None:
    """!h[elp] [{subject}]

    Show help about {subject}. When {subject} is not parsed show game help.
    """

    if not arg:
        pager(GAME_HELP)
        return

    commands = get_game().commands
    if arg == 'commands':
        pager('\n'.join([
            cmd.doc
            for cmd in commands
            if cmd.doc is not None
        ]))
    elif arg in commands:
        cmd = commands[arg]
        if cmd.doc is not None:
            print(cmd.doc)
        else:
            print(f"  Command {cmd} don't have documentation")
    else:
        raise CommandError(f"  No help for '{arg}'")


@Command.add(name='quit', shorthand='q')
def quit_cmd() -> NoReturn:
    """!q[uit]

    Stop playing.
    """
    raise QuitGame


@Command.add(name='stop', shorthand='s')
def stop_cmd() -> NoReturn:
    """!q[uit]

    Exit the game.
    """
    raise StopPlaying


@Command.add(shorthand='r')
def restart_cmd() -> NoReturn:
    """!r[estart]

    Restart the round.
    """
    raise RestartGame


@Command.add(name='difficulty', shorthand='d')
def difficulty_cmd(arg: str = '') -> None:
    """!d[ifficulty] [{difficulty_name} | {difficulty_key} | -l]

    Change difficulty to the given one. If not given directly show
    difficulty selection.
    """

    game = get_game()
    if not arg:
        try:
            difficulty = difficulty_selection()
        except CancelOperation:
            return
        else:
            raise RestartGame(difficulty=difficulty)

    if arg == '-l':
        print(tabulate(
            map(attrgetter('name', 'num_size', 'digs_range'), game.difs),
            headers=('Key', 'Difficulty', 'Size', 'Digits'),
            tablefmt='plain',
            showindex=game.difs.indexes,
        ))
        return

    try:
        difficulty = game.difs[int(arg) if arg.isdigit() else arg]
    except (KeyError, IndexError):
        raise CommandError(f"  There is no '{arg}' difficulty")
    else:
        raise RestartGame(difficulty=difficulty)


@Command.add(name='clear', shorthand='c')
def clear_cmd() -> None:
    """!c[lean]

    Clear screan.
    """
    if os.name in ('nt', 'dos'):
        subprocess.call('cls')
    elif os.name in ('linux', 'osx', 'posix'):
        subprocess.call('clear')
    else:
        clear()


@Command.add(shorthand='hi')
def history_cmd(arg: str = '') -> None:
    """!hi[story] [-c]

    Show history.
        '-c' - before showing history clear the screan
    """
    game = get_game()
    if arg == '-c':
        clear_cmd()
    elif arg:
        raise CommandError(f"  invalid argument '{arg}'")

    if game.round.steps == 0:
        print("History is empty")
        return

    print(tabulate(
        iter(game.round.history),
        headers=('Number', 'Bulls', 'Cows'),
        colalign=('center', 'center', 'center'),
        tablefmt='plain',
    ))


# ====================
# Difficulty selection
# ====================

@cli_window('Difficulty Selection')
def difficulty_selection() -> Difficulty:
    """Difficulty selection."""
    difs = get_game().difs
    table = tabulate(
        map(attrgetter('name', 'num_size', 'digs_range'), difs),
        headers=('Key', 'Difficulty', 'Size', 'Digits'),
        colalign=('right', 'left', 'center', 'center'),
        showindex=difs.indexes,
    )

    print('\n', table, '\n', sep='')

    while True:
        try:
            input_ = prompt(
                'Enter key: ',
                validator=MenuValidator(difs.indexes),
                validate_while_typing=False,
            ).strip()
        except EOFError:
            raise CancelOperation
        except KeyboardInterrupt:
            continue

        return difs[int(input_)]


# =====
# Round
# =====


class RoundValidator(Validator):

    def __init__(self, difficulty: Difficulty) -> None:
        self._difficulty = difficulty

    def validate(self, document: Document) -> None:
        input_: str = document.text.strip()

        digs_set = self._difficulty.digs_set
        num_size = self._difficulty.num_size

        if not input_.startswith(Command.PREFIX):
            # Check if number have wrong characters
            wrong_chars = set(input_) - digs_set
            if wrong_chars:
                raise ValidationError(
                    message=(
                        "Wrong characters: %s"
                        % ', '.join(map(lambda x: f"'{x}'", wrong_chars))
                    ),
                    cursor_position=max(
                        input_.rfind(dig) for dig in wrong_chars
                    ) + 1,
                )

            # Check length
            if len(input_) != num_size:
                raise ValidationError(
                    message=f"Digit must have {num_size} digits",
                    cursor_position=len(input_),
                )

            # Check that digits don't repeat
            digits = Counter(input_)
            rep_digs = {i for i, n in digits.items() if n > 1}
            if rep_digs:
                raise ValidationError(
                    message=(
                        "Number can't have repeated digits. %s repeated."
                        % ', '.join(map(lambda x: f"'{x}'", rep_digs))
                    ),
                    cursor_position=max(
                        input_.rfind(dig) for dig in rep_digs
                    ) + 1,
                )


class Round:
    """Round class."""

    ROUND_START = '\n===== Round started ======\n'
    ROUND_END = '\n======= Round ended ======\n'

    def __init__(self, difficulty: Difficulty) -> None:
        self._difficulty = difficulty
        self._history = History()

        self._draw_number()
        if sys.flags.dev_mode:
            print(self._number)

    def _draw_number(self) -> None:
        """Draw number digits from self.difficulty.digs_set."""
        self._number = ''.join(
            random.sample(self.difficulty.digs_set, self.difficulty.num_size)
        )

    @property
    def history(self) -> History:
        return self._history

    @property
    def steps(self) -> int:
        return len(self._history)

    @property
    def difficulty(self) -> Difficulty:
        return self._difficulty

    @property
    def toolbar(self) -> str:
        return "  |  ".join([
            f" Difficulty: {self.difficulty.name}",
            f"Size: {self.difficulty.num_size}",
            f"Digits: {self.difficulty.digs_range}",
        ])

    def run(self) -> int:
        """Run round loop.

        Return score."""
        print(self.ROUND_START)
        try:
            self.ps: PromptSession = PromptSession(
                bottom_toolbar=self.toolbar,
                validator=RoundValidator(self.difficulty),
                validate_while_typing=False,
            )
            while True:
                number = self._number_input()
                bulls, cows = self.comput_bullscows(number)
                self.history.add_record(number, bulls, cows)

                if bulls == self.difficulty.num_size:
                    print(f"\n *** You guessed in {self.steps} steps ***")
                    return self.steps

                print(f"  bulls: {bulls:>2}, cows: {cows:>2}")
        finally:
            print(self.ROUND_END)

    def comput_bullscows(self, guess: str) -> Tuple[int, int]:
        """Return bulls and cows for given input."""
        bulls, cows = 0, 0

        for g, n in zip(guess, self._number):
            if g == n:
                bulls += 1
            elif g in self._number:
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
                        raise StopPlaying
                    else:
                        continue
                except CancelOperation:
                    raise StopPlaying
                continue
            except KeyboardInterrupt:
                continue

            if not input_:
                continue

            if input_.startswith(Command.PREFIX):
                get_game().commands.parse_cmd(input_)
                continue

            return input_


# ============
# Menu actions
# ============


MenuAction = Callable[[], None]


class MenuValidator(Validator):

    def __init__(self, index: Container[int]) -> None:
        self._index = index

    def validate(self, document: Document) -> None:
        text: str = document.text.strip()

        if text.isdigit() and int(text) in self._index:
            return

        raise ValidationError(
            message="Invalid key",
            cursor_position=document.cursor_position,
        )


@cli_window('Main Menu')
def menu_selecton() -> MenuAction:
    actions = get_game().actions
    table = tabulate(
        actions.table(),
        headers=('Key', 'Action'),
        colalign=('left', 'right'),
    )

    print('\n', table, '\n', sep='')

    while True:
        try:
            input_ = prompt(
                'Enter key: ',
                validator=MenuValidator(get_game().actions.index),
                validate_while_typing=False,
            ).strip()
        except EOFError:
            raise QuitGame
        except KeyboardInterrupt:
            continue

        return actions[int(input_)]


class PlayerValidator(Validator):

    def validate(self, document: Document) -> None:
        text = document.text.strip()
        min_len, max_len = 3, 20

        if len(text) < min_len:
            raise ValidationError(
                message=(
                    "Too short name. "
                    f"At least {min_len} characters needed."
                ),
                cursor_position=document.cursor_position,
            )

        if len(text) > max_len:
            raise ValidationError(
                message=(
                    "Too long name. "
                    f"Maximum {max_len} characters allowed."
                ),
                cursor_position=document.cursor_position,
            )


player_validator = PlayerValidator()


def play_action() -> None:

    RANKINGS_DIR.mkdir(exist_ok=True)

    try:
        difficulty = difficulty_selection()
    except CancelOperation:
        return

    ask_player_name: PromptSession = PromptSession(
        validator=player_validator,
        validate_while_typing=False,
    )

    game = get_game()

    while True:
        try:
            game.round = Round(difficulty)
            score = game.round.run()
        except RestartGame as rg:
            if rg.difficulty is not None:
                difficulty = rg.difficulty
            continue
        except StopPlaying:
            return
        finally:
            del game.round

        ranking_file = (
            RANKINGS_DIR
            / f'{difficulty.digs_num}_{difficulty.num_size}.csv'
        )
        ranking_file.touch()

        ranking = pd.read_csv(
            ranking_file,
            names=['datetime', 'score', 'player'],
            parse_dates=['datetime'],
        )

        if (
                len(ranking) >= RANKING_SIZE
                and ranking.score.iat[-1] <= score
        ):
            continue

        while True:
            try:
                player = ask_player_name.prompt('Save score as: ').strip()
            except EOFError:
                break
            except KeyboardInterrupt:
                continue

            try:
                if not ask_ok(f'Confirm player: "{player}" [Y/n] '):
                    continue
            except CancelOperation:
                break

            ranking = (
                ranking.append(
                    {
                        'datetime': datetime.now(),
                        'score': score,
                        'player': player,
                    },
                    ignore_index=True,
                )
                .sort_values(by=['score', 'datetime'])
                .head(RANKING_SIZE)
            )

            ranking.to_csv(ranking_file, header=False, index=False)

            show_ranking(ranking)

            break


def help_action() -> None:
    pager(GAME_HELP)


@cli_window('Show Ranking')
def show_ranking_action() -> None:
    RANKINGS_DIR.mkdir(exist_ok=True)

    ranking_files = []
    for file in RANKINGS_DIR.glob('*.csv'):
        digs_num, sep, num_size = file.stem.partition('_')
        if sep or digs_num.isdigit() or num_size.isdigit():
            ranking_files.append((digs_num, num_size, file))

    if not ranking_files:
        print('\nEmpty rankings\n')
        return

    ranking_groups = pd.DataFrame(
        sorted(ranking_files, key=itemgetter(1, 0)),
        index=pd.RangeIndex(1, len(ranking_files) + 1, name='Key'),
        columns=['Digits', 'Size', 'file'],
    )

    table = tabulate(
        ranking_groups[['Digits', 'Size']],
        headers='keys',
        colalign=('left', 'center', 'center'),
    )

    print('\n', table, '\n', sep='')

    while True:
        try:
            input_ = prompt(
                'Enter key: ',
                validator=MenuValidator(ranking_groups.index),
                validate_while_typing=False,
            ).strip()
        except EOFError:
            return
        except KeyboardInterrupt:
            continue

        ranking_file = ranking_groups.loc[int(input_)].file
        ranking = pd.read_csv(
            ranking_file,
            names=['datetime', 'score', 'player'],
            parse_dates=['datetime'],
        )

        show_ranking(ranking)


def quit_action() -> NoReturn:
    raise QuitGame


class ActionContainer:
    """Contain Command objects and allows execute them."""

    def __init__(self) -> None:
        self._actions = pd.DataFrame(
            [
                ['Play', play_action],
                ['Show rankings', show_ranking_action],
                ['Show help', help_action],
                ['EXIT', quit_action],
            ],
            columns=['label', 'action'],
            index=[1, 2, 3, 0],
        )

    def __getitem__(self, key: int) -> MenuAction:
        """Get Command by index."""
        return self._actions.loc[key].action

    @property
    def index(self) -> pd.Index:
        return self._actions.index

    def table(self) -> pd.DataFrame:
        return self._actions[['label']]


# ====
# Game
# ====


class Game:
    """Game class."""

    round: Round

    def __init__(self) -> None:
        self.difs = DifficultyContainer()
        self.commands = CommandContainer()
        self.actions = ActionContainer()

    def _print_starting_header(self) -> None:
        line = '=' * len(VERSION_STR)
        print('\n'.join([line, VERSION_STR, line]))

    def run(self) -> None:
        """Runs game loop.

        While this method is running `get_game()` will return caller
        of that method.
        """
        token = _current_game.set(self)
        try:
            self._print_starting_header()
            while True:
                try:
                    action = menu_selecton()
                    action()
                except QuitGame:
                    return

        finally:
            _current_game.reset(token)


_current_game: ContextVar[Game] = ContextVar('game')


class _MISSING_TYPE:
    """Singleton to use as missing value."""

    _instance: ClassVar[Optional['_MISSING_TYPE']] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


MISSING = _MISSING_TYPE()


@overload
def get_game(default: _MISSING_TYPE = MISSING) -> Game: ...


@overload
def get_game(default: Union[T, _MISSING_TYPE]) -> Union[Game, T]: ...


def get_game(default=MISSING):
    if default is not MISSING:
        return _current_game.get(default)
    return _current_game.get()


def run() -> None:
    Game().run()


if __name__ == '__main__':
    run()
