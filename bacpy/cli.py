from __future__ import annotations

from abc import ABCMeta, abstractmethod
from collections import Counter
from contextlib import ContextDecorator, contextmanager
import inspect
import itertools
from operator import attrgetter
from pathlib import Path
import shlex
import subprocess
import sys
from typing import (
    Callable,
    ClassVar,
    Container,
    Iterable,
    Iterator,
    KeysView,
    List,
    NoReturn,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from prompt_toolkit import PromptSession
from prompt_toolkit.document import Document
from prompt_toolkit.shortcuts import prompt
from prompt_toolkit.validation import Validator, ValidationError
from tabulate import tabulate

from .core import (
    DEFAULT_DIFFICULTIES,
    Difficulty,
    draw_number,
    PLAYER_NAME_LIMS,
    QuitGame,
    Ranking,
    RankingManager,
    RANKING_SIZE,
    RANKINGS_DIR,
    RestartGame,
    RoundCore,
    SimpleDifficulty,
    StopPlaying,
)

if sys.version_info >= (3, 8):
    import importlib.metadata as importlib_metadata
    from typing import Final, Literal
else:
    import importlib_metadata
    from typing_extensions import Final, Literal


# Type variables
T = TypeVar("T")


# Constants
PROGRAM_NAME: Final[str] = "BacPy"
PROGRAM_VERSION: Final[str] = (
    f" {PROGRAM_NAME} v{importlib_metadata.version('bacpy')} "
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


# ========
# Run game
# ========


def run_game() -> None:
    RANKINGS_DIR.mkdir(exist_ok=True)
    game = Game(RANKINGS_DIR)
    print(_starting_header(PROGRAM_VERSION))

    try:
        difficulty = difficulty_selection(game.difficulties)
    except EOFError:
        return

    player_name_iter = player_name_getter()

    while True:
        print()
        try:
            with game.set_round(
                    RoundCore(draw_number(difficulty), difficulty)
            ) as round_core:
                number_getter = _number_getter(
                    round_core.difficulty,
                    lambda: round_core.steps,
                    game.commands,
                )
                play_round(
                    round_core,
                    number_getter,
                    player_name_iter,
                    game.ranking_manager,
                )
        except RestartGame as rg:
            if rg.difficulty is not None:
                difficulty = rg.difficulty
            continue
        except (StopPlaying, QuitGame):
            return


def _starting_header(title: str) -> str:
    line = "=" * len(title)
    return f"{line}\n{title}\n{line}"


def play_round(
        round_core: RoundCore,
        number_getter: Iterator[str],
        player_name_iter: Iterator[Optional[str]],
        ranking_manager: RankingManager,
) -> None:
    while not round_core.finished:
        _, bulls, cows = round_core.parse_guess(next(number_getter))
        print(f"bulls: {bulls:>2}, cows: {cows:>2}")

    print(f"\n *** You guessed in {round_core.steps} steps ***\n")

    score_data = round_core.score_data
    if ranking_manager.is_score_fit_into(score_data):
        player = next(player_name_iter)
        if player:
            ranking = ranking_manager.update(score_data, player)
            pager(ranking_table(ranking))


# ====
# Game
# ====


class Game:
    """Game class."""

    def __init__(self, rankings_dir: Path) -> None:
        self._round: Optional[RoundCore] = None
        self.difficulties = Difficulties(DEFAULT_DIFFICULTIES)
        self.commands = get_commands(self)
        self.ranking_manager = RankingManager(rankings_dir)

    @property
    def round(self) -> RoundCore:
        if self._round is not None:
            return self._round
        raise AttributeError("Round not set now")

    @contextmanager
    def set_round(self, round_: RoundCore) -> Iterator[RoundCore]:
        try:
            self._round = round_
            yield round_
        finally:
            self._round = None


# ============
# Difficulties
# ============


class SimpleDifficulties:

    def __init__(self, data: Iterable[SimpleDifficulty]) -> None:
        self.data = tuple(data)
        self.by_attrs = {
            (dif.num_size, dif.digs_num): dif
            for dif in self.data
        }
        self.indexes = range(IDX_START, len(self.data) + IDX_START)

    def __iter__(self) -> Iterator[SimpleDifficulty]:
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, key: Union[Tuple[int, int], int]) -> SimpleDifficulty:
        """Return Difficulty by given attributes (`num_size`, `digs_num`)
        or index.
        """
        if isinstance(key, int):
            try:
                index = self.indexes.index(key)
            except ValueError:
                raise IndexError(key) from None
            return self.data[index]
        return self.by_attrs[key]

    @property
    def attrs(self) -> KeysView[Tuple[int, int]]:
        return self.by_attrs.keys()


class Difficulties:
    """Keeps available difficulties."""

    def __init__(self, data: Iterable[Difficulty]) -> None:
        self.data = data = tuple(data)
        self.by_name = {dif.name: dif for dif in data if dif.name}
        self.indexes = range(IDX_START, len(data) + IDX_START)

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
            return self.by_name[key]
        raise TypeError(
            f"Given key have wrong type ({type(key)}). "
            "'str' or 'int' needed."
        )

    @property
    def names(self) -> KeysView[str]:
        return self.by_name.keys()


# =========
# CLI tools
# =========


class cli_window(ContextDecorator):

    def __init__(
            self, header: str,
            fillchar: str = "=",
            wing_size: int = 5,
    ) -> None:
        self.header = header
        self.fillchar = fillchar
        self.wing_size = wing_size
        self.width = len(header) + 2 * (wing_size + 1)  # +1 is for space

    def __enter__(self):
        wing = self.fillchar * self.wing_size
        print(f"\n{wing} {self.header} {wing}")
        return self

    def __exit__(self, *exc):
        print(self.fillchar * self.width)
        return False


def ask_ok(prompt_message: str, default: Optional[bool] = True) -> bool:
    """Yes/No input.

    Can raise EOFError
    """
    while True:
        try:
            input_ = prompt(prompt_message).strip().lower()
        except KeyboardInterrupt:
            continue

        if not input_ and default is not None:
            return default
        if "yes".startswith(input_):
            return True
        if "no".startswith(input_):
            return False


def pager(text: str) -> None:
    """Use pager to show text."""
    # '-C' flag prevent from showing text on bottom of the screen
    subprocess.run(["less", "-C"], input=text.encode())


def ranking_table(ranking: Ranking) -> str:
    data = [
        (index, score, player)
        for index, (score, _, player) in itertools.zip_longest(
            range(1, RANKING_SIZE + 1),
            ranking.data,
            fillvalue=("-", None, "-"),
        )
    ]
    return tabulate(
        data,
        headers=("Pos.", "Score", "Player"),
        colalign=("left", "center", "left"),
    )


def simple_difficulties_table(difficulties: SimpleDifficulties) -> str:
    table = tabulate(
        map(attrgetter("num_size", "digs_num"), difficulties),
        headers=("Key", "Size", "Digits"),
        colalign=("right", "center", "center"),
        showindex=difficulties.indexes,
    )
    return f"\n{table}\n"


def difficulties_table(difficulties: Difficulties) -> str:
    table = tabulate(
        map(attrgetter("name", "num_size", "digs_range"), difficulties),
        headers=("Key", "Difficulty", "Size", "Digits"),
        colalign=("right", "left", "center", "center"),
        showindex=difficulties.indexes,
    )
    return f"\n{table}\n"


# ========
# Commands
# ========


COMMAND_PREFIX: Final[str] = "!"


class Command(metaclass=ABCMeta):
    """Command abstract class."""

    shorthand: ClassVar[Optional[str]] = None

    def __init__(self, game: Game) -> None:
        self.game = game
        self.args_range = _get_args_lims(self.execute)

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


def _get_args_lims(func: Callable) -> Tuple[int, float]:
    params = inspect.signature(func).parameters.values()
    min_, max_ = 0, 0
    for param in params:
        if param.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD:
            if param.default is inspect.Parameter.empty:
                min_ += 1
            max_ += 1
        elif param.kind is inspect.Parameter.VAR_POSITIONAL:
            return min_, float("inf")
    return min_, max_


class Commands:
    """Store `Command`'s and let take it by name or shorthand."""

    def __init__(self, cmds: Iterable[Command]) -> None:
        self.data = data = tuple(cmds)
        self.by_name = {
            cmd.name: cmd
            for cmd in data
        }
        self.by_shorthand = {
            cmd.shorthand: cmd
            for cmd in data
            if cmd.shorthand
        }

    def __iter__(self) -> Iterator[Command]:
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, key: str) -> Command:
        """Return Command by given name or shorthand."""
        try:
            return self.by_shorthand[key]
        except KeyError:
            return self.by_name[key]

    def __contains__(self, key: str) -> bool:
        return key in self.by_name or key in self.by_shorthand

    @property
    def names(self) -> KeysView[str]:
        return self.by_name.keys()

    @property
    def shorthands(self) -> KeysView[str]:
        return self.by_shorthand.keys()


def get_commands(
        game: Game,
        *,
        command_classes: Optional[Iterable[Type[Command]]] = None,
) -> Commands:
    command_classes = (
        command_classes
        if command_classes is not None
        else Command.__subclasses__()
    )
    return Commands(
        command_cls(game)
        for command_cls in command_classes
    )


class HelpCmd(Command):
    """
    h[elp] [{subject}]

        Show help about {subject}. When {subject} is not parsed show game help.
    """

    name = "help"
    shorthand = "h"

    def execute(self, arg: str = "") -> None:

        if not arg:
            pager(GAME_HELP)
            return

        commands = self.game.commands
        if arg == "commands":
            docs = (
                inspect.getdoc(cmd)
                for cmd in commands
            )
            pager("\n\n\n".join([
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
            print(f"No command '{arg}'")


class QuitCmd(Command):
    """
    q[uit]

        Stop playing.
    """

    name = "quit"
    shorthand = "q"

    def execute(self) -> NoReturn:
        raise QuitGame


class StopCmd(Command):
    """
    s[top]

        Exit the game.
    """

    name = "stop"
    shorthand = "s"

    def execute(self) -> NoReturn:
        raise StopPlaying


class RestartCmd(Command):
    """
    r[estart] [-l | -i | {difficulty_key} | {difficulty_name}]

        Restart the round. If argument given change difficulty.

        -l  List difficulties.

        -i  Interactively choose new difficulty.
    """
    name = "restart"
    shorthand = "r"

    def execute(self, arg: str = "") -> None:

        if not arg:
            raise RestartGame

        difficulties = self.game.difficulties

        if arg == "-i":
            try:
                difficulty = difficulty_selection(difficulties)
            except EOFError:
                return
        elif arg == "-l":
            print(difficulties_table(difficulties))
            return
        else:
            try:
                difficulty = difficulties[int(arg) if arg.isdigit() else arg]
            except KeyError:
                print(f"No '{arg}' difficulty available")
                return
            except IndexError:
                print(f"Invalid key '{arg}'")
                return

        raise RestartGame(difficulty=difficulty)


class HistoryCmd(Command):
    """
    hi[story]

        Show history.
    """

    name = "history"
    shorthand = "hi"

    def execute(self) -> None:

        if self.game.round.steps == 0:
            print("History is empty")
            return

        print(tabulate(
            self.game.round.history,
            headers=("Number", "Bulls", "Cows"),
            colalign=("center", "center", "center"),
            tablefmt="plain",
        ))


class RankingCmd(Command):
    """
    ra[nking] [{difficulty_name} | {difficulty_key} | -l]

        Show ranking of given difficulty. If not given directly show
        difficulty selection.

            -l  List available ranking`s difficulties.
    """

    name = "ranking"
    shorthand = "ra"

    def execute(self, arg: str = "") -> None:

        difficulties = SimpleDifficulties(
            self.game.ranking_manager.available_difficulties()
        )

        if not difficulties:
            print("\nEmpty rankings\n")
            return

        if arg == "-l":
            print(simple_difficulties_table(difficulties))
            return
        elif arg:
            try:
                difficulty = difficulties[int(arg)]
            except IndexError:
                print(f"Invalid index '{arg}'")
                return
        else:
            try:
                difficulty = simple_difficulty_selection(difficulties)
            except EOFError:
                return

        pager(ranking_table(
            self.game.ranking_manager.load(difficulty)
        ))


# =====
# Menus
# =====


@cli_window("Difficulty Selection")
def simple_difficulty_selection(
        difficulties: SimpleDifficulties
) -> SimpleDifficulty:
    """SimpleDifficulty selection.

    Can raise EOFError."""

    print(simple_difficulties_table(difficulties))

    while True:
        try:
            input_ = prompt(
                "Enter key: ",
                validator=MenuValidator(difficulties.indexes),
                validate_while_typing=False,
            ).strip()
        except KeyboardInterrupt:
            continue

        return difficulties[int(input_)]


@cli_window("Difficulty Selection")
def difficulty_selection(difficulties: Difficulties) -> Difficulty:
    """Difficulty selection.

    Can raise EOFError."""

    print(difficulties_table(difficulties))

    while True:
        try:
            input_ = prompt(
                "Enter key: ",
                validator=MenuValidator(difficulties.indexes),
                validate_while_typing=False,
            ).strip()
        except KeyboardInterrupt:
            continue

        return difficulties[int(input_)]


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
                    % ", ".join(map(lambda x: f"'{x}'", wrong_chars))
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
                    % ", ".join(map(lambda x: f"'{x}'", rep_digs))
                ),
                cursor_position=max(
                    input_.rfind(dig) for dig in rep_digs
                ) + 1,
            )


class PlayerValidator(Validator):

    def validate(self, document: Document) -> None:
        text = document.text.strip()
        min_len, max_len = PLAYER_NAME_LIMS

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
    return "  |  ".join(
        [
            f"  Difficulty: {difficulty.name}",
            f"Size: {difficulty.num_size}",
            f"Digits: {difficulty.digs_range}",
        ]
    )


def _number_getter(
        difficulty: Difficulty,
        get_steps: Callable[[], int],
        commands: Commands,
) -> Iterator[str]:
    """Take number from user.

    Supports special input. Can raise `StopPlaying`.
    """
    prompt_session: PromptSession[str] = PromptSession(
        bottom_toolbar=_get_toolbar(difficulty),
        validator=RoundValidator(difficulty),
        validate_while_typing=False,
    )
    while True:
        try:
            input_ = prompt_session.prompt(f"[{get_steps() + 1}] ").lstrip()
        except EOFError:
            try:
                if ask_ok("Do you really want to quit? [Y/n]: "):
                    raise StopPlaying
                continue
            except EOFError:
                raise StopPlaying
        except KeyboardInterrupt:
            continue

        if not input_.startswith(COMMAND_PREFIX):
            yield input_.rstrip()
            continue

        cmd_line = input_[len(COMMAND_PREFIX):].lstrip()

        if not cmd_line:
            print(
                f"Type '{COMMAND_PREFIX}help commands' to get "
                "available commands"
            )
            continue

        cmd_name, *args = shlex.split(cmd_line)
        try:
            commands[cmd_name].parse_args(args)
        except KeyError:
            print(f"No command '{cmd_name}'")


def player_name_getter() -> Iterator[Optional[str]]:
    """Yields player name or `None` if `EOFError`."""
    prompt_session: PromptSession[str] = PromptSession(
        "Save score as: ",
        validator=player_validator,
        validate_while_typing=False,
        enable_history_search=True,
    )
    while True:
        try:
            player = prompt_session.prompt().strip()
        except EOFError:
            yield None
        except KeyboardInterrupt:
            continue

        try:
            if not ask_ok(f"Confirm player: '{player}' [Y/n] "):
                continue
        except EOFError:
            yield None

        yield player
