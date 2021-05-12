from abc import ABCMeta, abstractmethod
from collections import Counter
from contextlib import ContextDecorator, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
import inspect
from operator import attrgetter
import os
from pathlib import Path
import random
import shlex
import subprocess
import sys
from typing import (
    cast,
    ClassVar,
    Container,
    Deque,
    Dict,
    FrozenSet,
    Generator,
    Iterable,
    Iterator,
    KeysView,
    List,
    Mapping,
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
    from typing import Final, Literal
else:
    try:
        import importlib_metadata
    except ModuleNotFoundError:
        importlib_metadata = None

    from typing_extensions import Final, Literal

PROGRAM_NAME: Final[str] = "BacPy"
PROGRAM_VERSION: Final[str] = (
    f" {PROGRAM_NAME} v{importlib_metadata.version('bacpy')} "
    if importlib_metadata
    else f" {PROGRAM_NAME} "
)


# Type variables
T = TypeVar('T')

# Constants
RANKINGS_DIR: Final[Path] = Path('.rankings')
RANKINGS_DIR.mkdir(exist_ok=True)
IDX_START: Final[Literal[0, 1]] = 1
RANKING_SIZE: Final[int] = 10

GAME_HELP: Final[str] = """
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


DIGITS_RANGE: Final[str] = '123456789abcdef'


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

    def __init__(self, data: Optional[Iterable[Difficulty]] = None) -> None:
        if data is None:
            self._data = [
                Difficulty(*dif)
                for dif in [
                    (3, 6, 'easy'),
                    (4, 9, 'normal'),
                    (5, 15, 'hard'),
                ]
            ]
        else:
            self._data = list(data)

        self._mapping = {dif.name: dif for dif in self._data if dif.name}
        self._indexes = range(IDX_START, len(self) + IDX_START)

    def __iter__(self) -> Iterator[Difficulty]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __getitem__(self, key: Union[str, int]) -> Difficulty:
        """Return Difficulty by given name or index."""
        if isinstance(key, int):
            try:
                index = self.indexes.index(key)
            except ValueError:
                raise IndexError(key) from None
            return self._data[index]
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
        self._data: Deque[HistRecord] = Deque()

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


# =========
# CLI tools
# =========


class cli_window(ContextDecorator):

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
        print(f'\n{wing} {self.header} {wing}')
        return self

    def __exit__(self, *exc):
        print(self.fillchar * self.width, end='\n\n')
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


def show_difficulties_table(difficulties: DifficultyContainer) -> None:
    table = tabulate(
        map(attrgetter('name', 'num_size', 'digs_range'), difficulties),
        headers=('Key', 'Difficulty', 'Size', 'Digits'),
        colalign=('right', 'left', 'center', 'center'),
        showindex=difficulties.indexes,
    )
    print('\n', table, '\n', sep='')


# ========
# Commands
# ========


COMMAND_PREFIX: Final[str] = '!'


class Command(metaclass=ABCMeta):
    """Command abstract class."""

    shorthand: ClassVar[Optional[str]] = None

    def __init__(self, game: 'Game') -> None:
        self.game = game
        self._args_range = self._get_args_range()

    def _get_args_range(self) -> Tuple[int, float]:
        params = inspect.signature(self.execute).parameters.values()
        min_, max_ = 0, 0
        for param in params:
            if param.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD:
                if param.default is inspect.Parameter.empty:
                    min_ += 1
                max_ += 1
            elif param.kind is inspect.Parameter.VAR_POSITIONAL:
                return min_, float('inf')
        return min_, max_

    def parse_args(self, args: List[str]) -> None:
        """Execute command if valid number of arguments passed.

        If number of arguments is invalid print warning.
        """
        min_, max_ = self._args_range

        if min_ <= len(args) <= max_:
            self.execute(*args)

        if min_ == max_:
            print(
                f"'{self.name}' command get {min_} arguments. "
                f"{len(args)} was given."
            )
        else:
            print(
                f"'{self.name}' command get between {min_} and {max_} "
                f"arguments. {len(args)} was given."
            )

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def execute(self):
        """Execute command by parsing `str` type arguments."""


class CommandBase(Mapping[str, Command]):
    """Mapping of string keys and `Command` instanses values.

    Allows execute commands by `parse_cmd()`."""

    def __init__(self, game: 'Game') -> None:
        command_classes = Command.__subclasses__()
        commands = [
            # mypy issue -- shows that `Command` is in `command_classes`
            command(game)  # type: ignore[abstract]
            for command in command_classes
        ]
        self._mapping: Dict[str, Command] = {
            cmd.name: cmd
            for cmd in commands
        }
        self._shorthands_map: Dict[str, str] = {
            cmd.shorthand: cmd.name
            for cmd in commands
            if cmd.shorthand
        }

    def __iter__(self) -> Iterator[str]:
        """Iterate through names."""
        return iter(self._mapping)

    def __getitem__(self, key: str) -> Command:
        """Get Command by given name or shorthand."""
        if key in self._shorthands_map:
            return self._mapping[self._shorthands_map[key]]
        if key in self._mapping:
            return self._mapping[key]
        raise KeyError(key)

    def __len__(self) -> int:
        """Return number of Commands."""
        return len(self._mapping)

    def __contains__(self, key: object) -> bool:
        """Check if given name or shorthand is available."""
        return (
            key in self._mapping
            or key in self._shorthands_map
        )

    def keys(self) -> KeysView[str]:
        """Get names and shorthands view."""
        new_mapping: Mapping[str, object] = {
            **self._mapping,
            **self._shorthands_map,
        }
        return cast(
            # suppress mypy issue that shows AbstractSet[str] type
            KeysView[str],
            new_mapping.keys(),
        )

    def names(self) -> KeysView[str]:
        """Get names view."""
        return self._mapping.keys()

    def shorthands(self) -> KeysView[str]:
        """Get shorthands view."""
        return self._shorthands_map.keys()

    def parse_cmd(self, input_: str) -> None:
        """Search for command and execute it."""
        input_ = input_[len(COMMAND_PREFIX):]

        if not input_:
            return

        name, *args = shlex.split(input_)
        if name in self:
            self[name].parse_args(args)
        else:
            print(f"No command: {name}")


class HelpCmd(Command):
    """
    h[elp] [{subject}]

        Show help about {subject}. When {subject} is not parsed show game help.
    """

    name = 'help'
    shorthand = 'h'

    def execute(self, arg: str = '') -> None:

        if not arg:
            pager(GAME_HELP)
            return

        commands = self.game.commands
        if arg == 'commands':
            docs = (
                inspect.getdoc(cmd)
                for cmd in commands.values()
            )
            pager('\n\n\n'.join([
                doc
                for doc in docs
                if doc is not None
            ]))
        elif arg in commands:
            cmd = commands[arg]
            doc = inspect.getdoc(cmd)
            if doc is not None:
                print(doc)
            else:
                print(f"Command '{cmd.name}' don't have documentation")
        else:
            print(f"No command: {arg}")


class QuitCmd(Command):
    """
    q[uit]

        Stop playing.
    """

    name = 'quit'
    shorthand = 'q'

    def execute(self) -> NoReturn:
        raise QuitGame


class StopCmd(Command):
    """
    s[top]

        Exit the game.
    """

    name = 'stop'
    shorthand = 's'

    def execute(self) -> NoReturn:
        raise StopPlaying


class RestartCmd(Command):
    """
    r[estart]

        Restart the round.
    """

    name = 'restart'
    shorthand = 'r'

    def execute(self) -> NoReturn:
        print("\n-- Game restarted --\n")
        raise RestartGame


class DifficultyCmd(Command):
    """
    d[ifficulty] [{difficulty_name} | {difficulty_key} | -l]

        Change difficulty to the given one. If not given directly show
        difficulty selection.
    """

    name = 'difficulty'
    shorthand = 'd'

    def execute(self, arg: str = '') -> None:

        difficulties = self.game.difficulties

        if not arg:
            try:
                difficulty = difficulty_selection(difficulties)
            except CancelOperation:
                return
            else:
                raise RestartGame(difficulty=difficulty)

        if arg == '-l':
            show_difficulties_table(difficulties)
            return

        try:
            difficulty = difficulties[int(arg) if arg.isdigit() else arg]
        except KeyError:
            print(f"No '{arg}' difficulty available")
            return
        except IndexError:
            print(f"Invalid index: {arg}")
            return
        else:
            print("\n-- Difficulty changed --\n")
            raise RestartGame(difficulty=difficulty)


class ClearCmd(Command):
    """
    c[lean]

        Clear screan.
    """

    name = 'clear'
    shorthand = 'c'

    def execute(self) -> None:
        if os.name in ('nt', 'dos'):
            subprocess.call('cls')
        elif os.name in ('linux', 'osx', 'posix'):
            subprocess.call('clear')
        else:
            clear()


class HistoryCmd(Command):
    """
    hi[story] [-c]

        Show history.
            -c  before showing history clear the screan
    """

    name = 'history'
    shorthand = 'hi'

    def execute(self, arg: str = '') -> None:

        if arg == '-c':
            self.game.commands['clear'].execute()
        elif arg:
            print(f"Invalid argument '{arg}'")
            return

        if self.game.round.steps == 0:
            print("History is empty")
            return

        print(tabulate(
            iter(self.game.round.history),
            headers=('Number', 'Bulls', 'Cows'),
            colalign=('center', 'center', 'center'),
            tablefmt='plain',
        ))


class RankingCmd(Command):
    """
    ra[nking] [{difficulty_name} | {difficulty_key} | -l]

        Show ranking of given difficulty. If not given directly show
        difficulty selection.

            -l  List available ranking`s difficulties.
    """

    name = 'ranking'
    shorthand = 'ra'

    def execute(self, arg: str = '') -> None:

        difficulties = self.game.difficulties

        difficulties = available_rankings(difficulties)

        if not difficulties:
            print('\nEmpty rankings\n')
            return

        if arg == '-l':
            show_difficulties_table(difficulties)
            return
        elif arg:
            try:
                difficulty = difficulties[int(arg) if arg.isdigit() else arg]
            except KeyError:
                print(f"No '{arg}' difficulty available")
                return
            except IndexError:
                print(f"Invalid index: {arg}")
                return
        else:
            try:
                difficulty = difficulty_selection(difficulties)
            except CancelOperation:
                return

        show_ranking(load_ranking(difficulty))


# ==========
# Core tools
# ==========


def _get_ranking_path(difficulty: Difficulty) -> Path:
    return (
        RANKINGS_DIR
        / f'{difficulty.digs_num}_{difficulty.num_size}.csv'
    )


def available_rankings(
        difficulties: DifficultyContainer,
) -> DifficultyContainer:
    """Filter difficulties by the fact that corresponding ranking is
    available.
    """
    return DifficultyContainer(
        difficulty
        for difficulty in difficulties
        if _get_ranking_path(difficulty).exists()
    )


def load_ranking(difficulty: Difficulty) -> pd.DataFrame:
    """Read and return ranking by given difficulty."""
    path = _get_ranking_path(difficulty)
    path.touch()
    return pd.read_csv(
        path,
        names=['datetime', 'score', 'player'],
        parse_dates=['datetime'],
    )


def save_ranking(ranking: pd.DataFrame, difficulty: Difficulty) -> None:
    ranking.to_csv(
        _get_ranking_path(difficulty),
        header=False,
        index=False,
    )


class RankingUpdater:
    """Read ranking. Check if score fit in. If so, allow update it."""

    def __init__(self, difficulty: Difficulty, score: int) -> None:
        self._difficulty = difficulty
        self._score = score
        self._datetime = datetime.now()
        self._ranking = ranking = load_ranking(difficulty)
        self._is_score_fit_in = (
            len(ranking) >= RANKING_SIZE
            and ranking.score.iat[-1] <= score
        )

    @property
    def is_score_fit_in(self) -> bool:
        return self._is_score_fit_in

    def update(self, player: str) -> pd.DataFrame:

        ranking = (
            self._ranking
            .append(
                {
                    'datetime': self._datetime,
                    'score': self._score,
                    'player': player,
                },
                ignore_index=True,
            )
            .sort_values(by=['score', 'datetime'])
            .head(RANKING_SIZE)
        )

        save_ranking(ranking, self._difficulty)

        return ranking


# =====
# Menus
# =====


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


@cli_window('Difficulty Selection')
def difficulty_selection(difficulties: DifficultyContainer) -> Difficulty:
    """Difficulty selection."""

    show_difficulties_table(difficulties)

    while True:
        try:
            input_ = prompt(
                'Enter key: ',
                validator=MenuValidator(difficulties.indexes),
                validate_while_typing=False,
            ).strip()
        except EOFError:
            raise CancelOperation
        except KeyboardInterrupt:
            continue

        return difficulties[int(input_)]


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

        if input_.startswith(COMMAND_PREFIX):
            return

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

    def __init__(self, difficulty: Difficulty) -> None:
        self._difficulty = difficulty
        self._history = History()

        self.prompt_session: PromptSession = PromptSession(
            bottom_toolbar=self.toolbar,
            validator=RoundValidator(self.difficulty),
            validate_while_typing=False,
        )

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

        Return score.
        """
        while True:
            number = self._number_input()
            bulls, cows = self.comput_bullscows(number)
            self.history.add_record(number, bulls, cows)

            if bulls == self.difficulty.num_size:
                print(f"\n *** You guessed in {self.steps} steps ***\n")
                return self.steps

            print(f"  bulls: {bulls:>2}, cows: {cows:>2}")

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
                input_ = self.prompt_session.prompt(
                    f"[{self.steps + 1}] "
                ).strip()
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

            if input_.startswith(COMMAND_PREFIX):
                get_game().commands.parse_cmd(input_)
                continue

            return input_


# ====
# Game
# ====


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


class Game:
    """Game class."""

    def __init__(self) -> None:
        self._round: Optional[Round] = None
        self.difficulties = DifficultyContainer()
        self.commands = CommandBase(self)
        self._ask_player_name: PromptSession = PromptSession(
            validator=player_validator,
            validate_while_typing=False,
        )

    def _print_starting_header(self) -> None:
        line = '=' * len(PROGRAM_VERSION)
        print('\n'.join([line, PROGRAM_VERSION, line]))

    def run(self) -> None:
        """Runs game loop.

        While this method is running `get_game()` will return caller
        of that method.
        """
        token = _current_game.set(self)
        try:
            self._print_starting_header()
            self._run()
        except QuitGame:
            return
        finally:
            _current_game.reset(token)

    @property
    def round(self) -> Round:
        if self._round is not None:
            return self._round
        raise AttributeError("Round not set now")

    @contextmanager
    def set_round(self, round_: Round) -> Generator[Round, None, None]:
        try:
            self._round = round_
            yield round_
        finally:
            self._round = None

    def get_player_name(self) -> Optional[str]:
        """Ask for player name and return it.

        If operation canceled return `None`.
        """
        while True:
            try:
                player = self._ask_player_name.prompt(
                    'Save score as: '
                ).strip()
            except EOFError:
                return None
            except KeyboardInterrupt:
                continue

            try:
                if not ask_ok(f'Confirm player: "{player}" [Y/n] '):
                    continue
            except CancelOperation:
                return None

            return player

    def _run(self) -> None:

        try:
            difficulty = difficulty_selection(self.difficulties)
        except CancelOperation:
            return

        while True:
            try:
                with self.set_round(Round(difficulty)) as round_:
                    score = round_.run()
            except RestartGame as rg:
                if rg.difficulty is not None:
                    difficulty = rg.difficulty
                continue
            except StopPlaying:
                return

            ranking_updater = RankingUpdater(difficulty, score)

            if not RankingUpdater.is_score_fit_in:
                continue

            player = self.get_player_name()
            if player:
                ranking = ranking_updater.update(player)
                show_ranking(ranking)

            print()


_current_game: ContextVar[Game] = ContextVar('game')


class _MISSING_TYPE:
    """Singleton to use as missing value."""

    _instance: ClassVar[Optional['_MISSING_TYPE']] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


MISSING: Final[_MISSING_TYPE] = _MISSING_TYPE()


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
