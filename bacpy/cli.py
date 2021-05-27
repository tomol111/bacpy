from abc import ABCMeta, abstractmethod
from collections import Counter
from contextlib import ContextDecorator, contextmanager
from contextvars import ContextVar
import inspect
from operator import attrgetter
import os
import shlex
import subprocess
import sys
from typing import (
    cast,
    Callable,
    ClassVar,
    Container,
    Dict,
    Generator,
    Iterable,
    Iterator,
    KeysView,
    List,
    Mapping,
    NoReturn,
    Optional,
    overload,
    Tuple,
    TypeVar,
    Union,
)

import pandas as pd
from prompt_toolkit import PromptSession
from prompt_toolkit.document import Document
from prompt_toolkit.shortcuts import clear, prompt
from prompt_toolkit.validation import Validator, ValidationError
from tabulate import tabulate

from .core import (
    available_ranking_difficulties,
    DEFAULT_DIFFICULTIES,
    Difficulty,
    load_ranking,
    QuitGame,
    RANKING_SIZE,
    RANKINGS_DIR,
    RestartGame,
    RoundCore,
    StopPlaying,
)

if sys.version_info >= (3, 8):
    import importlib.metadata as importlib_metadata
    from typing import Final, Literal
else:
    try:
        import importlib_metadata
    except ModuleNotFoundError:
        importlib_metadata = None

    from typing_extensions import Final, Literal


# Type variables
T = TypeVar('T')


# Constants
PROGRAM_NAME: Final[str] = "BacPy"
PROGRAM_VERSION: Final[str] = (
    f" {PROGRAM_NAME} v{importlib_metadata.version('bacpy')} "
    if importlib_metadata
    else f" {PROGRAM_NAME} "
)
IDX_START: Final[Literal[0, 1]] = 1

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


# ===================
# DifficultyContainer
# ===================


class DifficultyContainer:
    """Keeps available difficulties."""

    def __init__(self, data: Iterable[Difficulty]) -> None:
        self.data = tuple(data)
        self.mapping = {dif.name: dif for dif in self.data if dif.name}
        self.indexes = range(IDX_START, len(self) + IDX_START)

    def __iter__(self) -> Iterator[Difficulty]:
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, key: Union[str, int]) -> Difficulty:
        """Return Difficulty by given name or index."""
        if isinstance(key, int):
            try:
                index = self.indexes.index(key)
            except ValueError:
                raise IndexError(key) from None
            return self.data[index]
        if isinstance(key, str):
            return self.mapping[key]
        raise TypeError(
            f"Given key have wrong type ({type(key)}). "
            "'str' or 'int' needed."
        )

    @property
    def names(self) -> KeysView[str]:
        return self.mapping.keys()

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
        print(self.fillchar * self.width)
        return False


def ask_ok(prompt_message: str, default: Optional[bool] = True) -> bool:
    """Yes/No input.

    Can raise EOFError"""
    while True:
        try:
            input_ = prompt(prompt_message).strip().lower()
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


def ranking_table(ranking: pd.DataFrame) -> str:
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

    return tabulate(
        ranking,
        headers='keys',
        colalign=('left', 'center', 'left'),
    )


def difficulties_table(difficulties: DifficultyContainer) -> str:
    table = tabulate(
        map(attrgetter('name', 'num_size', 'digs_range'), difficulties),
        headers=('Key', 'Difficulty', 'Size', 'Digits'),
        colalign=('right', 'left', 'center', 'center'),
        showindex=difficulties.indexes,
    )
    return f'\n{table}\n'


# ========
# Commands
# ========


COMMAND_PREFIX: Final[str] = '!'


class Command(metaclass=ABCMeta):
    """Command abstract class."""

    shorthand: ClassVar[Optional[str]] = None

    def __init__(self, game: 'Game') -> None:
        self.game = game
        self.args_range = self._get_args_range()

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
        min_, max_ = self.args_range

        if min_ <= len(args) <= max_:
            self.execute(*args)
        elif min_ == max_:
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
        self.mapping: Dict[str, Command] = {
            cmd.name: cmd
            for cmd in commands
        }
        self.shorthands_map: Dict[str, str] = {
            cmd.shorthand: cmd.name
            for cmd in commands
            if cmd.shorthand
        }

    def __iter__(self) -> Iterator[str]:
        """Iterate through names."""
        return iter(self.mapping)

    def __getitem__(self, key: str) -> Command:
        """Get Command by given name or shorthand."""
        if key in self.shorthands_map:
            return self.mapping[self.shorthands_map[key]]
        if key in self.mapping:
            return self.mapping[key]
        raise KeyError(key)

    def __len__(self) -> int:
        """Return number of Commands."""
        return len(self.mapping)

    def __contains__(self, key: object) -> bool:
        """Check if given name or shorthand is available."""
        return (
            key in self.mapping
            or key in self.shorthands_map
        )

    def keys(self) -> KeysView[str]:
        """Get names and shorthands view."""
        new_mapping: Mapping[str, object] = {
            **self.mapping,
            **self.shorthands_map,
        }
        return cast(
            # suppress mypy issue that shows AbstractSet[str] type
            KeysView[str],
            new_mapping.keys(),
        )

    def names(self) -> KeysView[str]:
        """Get names view."""
        return self.mapping.keys()

    def shorthands(self) -> KeysView[str]:
        """Get shorthands view."""
        return self.shorthands_map.keys()

    def parse_cmd(self, input_: str) -> None:
        """Search for command and execute it."""
        input_ = input_[len(COMMAND_PREFIX):]

        if not input_:
            print("Type '!help commands' to get available commands")
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
    r[estart] [-l | -i | {difficulty_key} | {difficulty_name}]

        Restart the round. If argument given change difficulty.

        -l  List difficulties.

        -i  Interactively choose new difficulty.
    """
    name = 'restart'
    shorthand = 'r'

    def execute(self, arg: str = '') -> None:

        if not arg:
            raise RestartGame

        difficulties = self.game.difficulties

        if arg == '-i':
            try:
                difficulty = difficulty_selection(difficulties)
            except EOFError:
                return
        elif arg == '-l':
            print(difficulties_table(difficulties))
            return
        else:
            try:
                difficulty = difficulties[int(arg) if arg.isdigit() else arg]
            except KeyError:
                print(f"No '{arg}' difficulty available")
                return
            except IndexError:
                print(f"Invalid key: {arg}")
                return

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
            self.game.round.history,
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

        difficulties = DifficultyContainer(
            available_ranking_difficulties(difficulties)
        )

        if not difficulties:
            print('\nEmpty rankings\n')
            return

        if arg == '-l':
            print(difficulties_table(difficulties))
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
            except EOFError:
                return

        pager(ranking_table(load_ranking(difficulty)))


# =====
# Menus
# =====


class MenuValidator(Validator):

    def __init__(self, index: Container[int]) -> None:
        self.index = index

    def validate(self, document: Document) -> None:
        text: str = document.text.strip()

        if text.isdigit() and int(text) in self.index:
            return

        raise ValidationError(
            message="Invalid key",
            cursor_position=document.cursor_position,
        )


@cli_window('Difficulty Selection')
def difficulty_selection(difficulties: DifficultyContainer) -> Difficulty:
    """Difficulty selection.

    Can raise EOFError."""

    print(difficulties_table(difficulties))

    while True:
        try:
            input_ = prompt(
                'Enter key: ',
                validator=MenuValidator(difficulties.indexes),
                validate_while_typing=False,
            ).strip()
        except KeyboardInterrupt:
            continue

        return difficulties[int(input_)]


class RoundValidator(Validator):

    def __init__(self, difficulty: Difficulty) -> None:
        self.difficulty = difficulty

    def validate(self, document: Document) -> None:
        input_: str = document.text.strip()

        digs_set = self.difficulty.digs_set
        num_size = self.difficulty.num_size

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


def _get_toolbar(difficulty: Difficulty) -> str:
    return "  |  ".join([
        f"  Difficulty: {difficulty.name}",
        f"Size: {difficulty.num_size}",
        f"Digits: {difficulty.digs_range}",
    ])


def _number_getter(
        difficulty: Difficulty,
        get_steps: Callable[[], int],
) -> Generator[str, None, None]:
    """Take number from user.

    Supports special input. Can raise `StopPlaying`.
    """
    prompt_session: PromptSession = PromptSession(
        bottom_toolbar=_get_toolbar(difficulty),
        validator=RoundValidator(difficulty),
        validate_while_typing=False,
    )
    while True:
        try:
            input_ = prompt_session.prompt(f"[{get_steps() + 1}] ").strip()
        except EOFError:
            try:
                if ask_ok('Do you really want to quit? [Y/n]: '):
                    raise StopPlaying
                continue
            except EOFError:
                raise StopPlaying
        except KeyboardInterrupt:
            continue

        if input_.startswith(COMMAND_PREFIX):
            get_game().commands.parse_cmd(input_)
            continue

        yield input_


def _get_player_name() -> Optional[str]:
    """Ask for player name and return it."""
    while True:
        try:
            player = prompt(
                'Save score as: ',
                validator=player_validator,
                validate_while_typing=False,
            ).strip()
        except EOFError:
            return None
        except KeyboardInterrupt:
            continue

        try:
            if not ask_ok(f'Confirm player: "{player}" [Y/n] '):
                continue
        except EOFError:
            return None

        return player


def play(round_core: RoundCore) -> None:
    number_getter = _number_getter(
        round_core.difficulty,
        lambda: round_core.steps,
    )

    while not round_core.finished:
        number = next(number_getter)
        _, bulls, cows = round_core.parse_guess(number)
        print(f"bulls: {bulls:>2}, cows: {bulls:>2}")

    print(f"\n *** You guessed in {round_core.steps} steps ***\n")

    if round_core.score_fit_in:
        player = _get_player_name()
        if player:
            ranking = round_core.update_ranking(player)
            pager(ranking_table(ranking))


# ====
# Game
# ====


def _starting_header(title: str = PROGRAM_VERSION) -> str:
    line = '=' * len(title)
    return f'{line}\n{title}\n{line}'


class Game:
    """Game class."""

    def __init__(self) -> None:
        self._round: Optional[RoundCore] = None
        self.difficulties = DifficultyContainer(DEFAULT_DIFFICULTIES)
        self.commands = CommandBase(self)

    @property
    def round(self) -> RoundCore:
        if self._round is not None:
            return self._round
        raise AttributeError("Round not set now")

    @contextmanager
    def set_round(self, round_: RoundCore) -> Generator[RoundCore, None, None]:
        try:
            self._round = round_
            yield round_
        finally:
            self._round = None


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


# ========
# Run game
# ========


def _run_game(game: Game) -> None:
    try:
        difficulty = difficulty_selection(game.difficulties)
    except EOFError:
        return

    while True:
        print()
        try:
            with game.set_round(RoundCore(difficulty)) as round_:
                play(round_)
        except RestartGame as rg:
            if rg.difficulty is not None:
                difficulty = rg.difficulty
            continue
        except StopPlaying:
            return


def run_game() -> None:
    RANKINGS_DIR.mkdir(exist_ok=True)
    game = Game()
    token = _current_game.set(game)
    try:
        print(_starting_header())
        _run_game(game)
    except QuitGame:
        return
    finally:
        _current_game.reset(token)