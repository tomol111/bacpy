from __future__ import annotations

from abc import ABCMeta, abstractmethod
from contextlib import ContextDecorator, contextmanager
from importlib import metadata
import inspect
import itertools
from operator import attrgetter
import shlex
import subprocess
import sys
from typing import (
    Callable,
    ClassVar,
    Final,
    Iterable,
    Iterator,
    KeysView,
    List,
    Literal,
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

from bacpy.core import (
    DEFAULT_NUMBER_PARAMETERS,
    draw_number,
    GuessHandler,
    NumberParams,
    QuitGame,
    Ranking,
    RankingRepo,
    RANKING_SIZE,
    RestartGame,
    Difficulty,
    StopPlaying,
    validate_number,
    validate_player_name,
)
from bacpy.file_ranking import FileRankingRepo, RANKINGS_DIR


# Type variables
T = TypeVar("T")


# Constants
PROGRAM_NAME: Final[str] = "BacPy"
PROGRAM_VERSION: Final[str] = (
    f" {PROGRAM_NAME} v{metadata.version('bacpy')} "
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
    game = Game(FileRankingRepo(RANKINGS_DIR))
    print(starting_header(PROGRAM_VERSION))

    try:
        number_params = number_params_selection(game.number_params_container)
    except EOFError:
        return

    player_name_iter = player_name_getter()

    while True:
        print()
        try:
            secret_number = draw_number(number_params)

            if sys.flags.dev_mode:  # logging on console
                print(f"secret number: {secret_number}")

            guess_handler = GuessHandler(secret_number, number_params)
            with game.set_guess_handler(guess_handler):
                number_iter = number_getter(
                    number_params,
                    lambda: guess_handler.steps_done,
                    game.commands,
                )
                play_round(
                    guess_handler,
                    number_iter,
                    player_name_iter,
                    game.ranking_repo,
                )
        except RestartGame as rg:
            if rg.number_params is not None:
                number_params = rg.number_params
            continue
        except (StopPlaying, QuitGame):
            return


def starting_header(title: str) -> str:
    line = "=" * len(title)
    return f"{line}\n{title}\n{line}"


def play_round(
        guess_handler: GuessHandler,
        number_iter: Iterator[str],
        player_name_iter: Iterator[Optional[str]],
        ranking_repo: RankingRepo,
) -> None:
    for bulls, cows in map(guess_handler.send, number_iter):
        print(f"bulls: {bulls:>2}, cows: {cows:>2}")

    print(f"\n*** You guessed in {guess_handler.steps_done} steps ***\n")

    if (
            ranking_repo.is_score_fit_into(guess_handler.score_data)
            and (player := next(player_name_iter))
    ):
        ranking = ranking_repo.update(guess_handler.score_data, player)
        pager(ranking_table(ranking))


# ====
# Game
# ====


class Game:
    """Game class."""

    def __init__(self, ranking_repo: RankingRepo) -> None:
        self._guess_handler: Optional[GuessHandler] = None
        self.number_params_container = NumberParamsContainer(DEFAULT_NUMBER_PARAMETERS)
        self.commands = get_commands(self)
        self.ranking_repo = ranking_repo

    @property
    def guess_handler(self) -> GuessHandler:
        if self._guess_handler is not None:
            return self._guess_handler
        raise AttributeError("Round not set now")

    @contextmanager
    def set_guess_handler(self, guess_handler: GuessHandler) -> Iterator[None]:
        self._guess_handler = guess_handler
        try:
            yield
        finally:
            self._guess_handler = None


# =========
# CLI tools
# =========


class cli_window(ContextDecorator):

    def __init__(
            self,
            header: str,
            fillchar: str = "=",
            wing_size: int = 5,
    ) -> None:
        self.header = header
        self.fillchar = fillchar
        self.wing_size = wing_size
        self.width = len(header) + 2 * (wing_size + 1)  # +1 is for space

    def __enter__(self):
        wing = self.fillchar * self.wing_size
        print(f"{wing} {self.header} {wing}")
        return self

    def __exit__(self, *exc):
        print(self.fillchar * self.width)
        return False


def ask_ok(
        prompt_message: str,
        *,
        prompt_func: Callable[[str], str] = prompt,
        default: Optional[bool] = True,
) -> bool:
    """Yes/No input.

    Can raise EOFError
    """
    while True:
        try:
            input_ = prompt_func(prompt_message).lower()
        except KeyboardInterrupt:
            continue

        if not input_:
            if default is not None:
                return default
            else:
                continue
        if "yes".startswith(input_):
            return True
        if "no".startswith(input_):
            return False


def pager(text: str) -> None:
    """Use pager to show text."""
    # '-C' flag prevent from showing text on bottom of the screen
    subprocess.run(["less", "-C"], input=text.encode())


# ===========
# Main prompt
# ===========


def number_getter(
        number_params: NumberParams,
        get_steps_done: Callable[[], int],
        commands: Commands,
) -> Iterator[str]:
    """Take number from user.

    Supports special input. Can raise `StopPlaying`.
    """
    prompt_session: PromptSession[str] = PromptSession(
        bottom_toolbar=get_toolbar(number_params),
        validator=MainPromptValidator(number_params),
        validate_while_typing=False,
    )
    while True:
        try:
            input_ = prompt_session.prompt(f"[{get_steps_done() + 1}] ")
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
            yield input_
            continue

        cmd_line = input_[len(COMMAND_PREFIX):]

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


class MainPromptValidator(Validator):

    def __init__(self, number_params: NumberParams) -> None:
        self.number_params = number_params

    def validate(self, document: Document) -> None:
        input_ = document.text

        try:
            if input_.startswith(COMMAND_PREFIX):
                validate_command(input_[len(COMMAND_PREFIX):])
            else:
                validate_number(input_, self.number_params)
        except ValueError as err:
            raise ValidationError(
                message=str(err),
                cursor_position=document.cursor_position,
            ) from err


def get_toolbar(number_params: NumberParams) -> str:
    return " | ".join(
        [
            f"Label: {number_params.label}",
            f"Size: {number_params.number_size}",
            f"Digits: {number_params.digits_description}",
        ]
    )


# ===================
# Getting player name
# ===================


def player_name_getter() -> Iterator[Optional[str]]:
    """Yields player name or `None` if `EOFError`."""
    prompt_session: PromptSession[str] = PromptSession(
        "Save score as: ",
        validator=PlayerNameValidator(),
        validate_while_typing=False,
        enable_history_search=True,
    )
    while True:
        try:
            player = prompt_session.prompt()
            if not ask_ok(f"Confirm player: '{player}' [Y/n] "):
                continue
        except KeyboardInterrupt:
            continue
        except EOFError:
            yield None
        else:
            yield player


class PlayerNameValidator(Validator):

    def validate(self, document: Document) -> None:
        try:
            validate_player_name(document.text)
        except ValueError as err:
            raise ValidationError(
                message=str(err),
                cursor_position=document.cursor_position,
            )


# ============
# Difficulties
# ============


class DifficultyContainer:

    def __init__(self, data: Iterable[Difficulty]) -> None:
        self.data = tuple(data)
        self.by_attrs = {
            (dif.number_size, dif.digits_num): dif
            for dif in self.data
        }
        self.indexes = range(IDX_START, len(self.data) + IDX_START)

    def __iter__(self) -> Iterator[Difficulty]:
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, key: Union[Tuple[int, int], int]) -> Difficulty:
        """Return Difficulty by given attributes (`number_size`, `digits_num`) or index.
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


class NumberParamsContainer:

    def __init__(self, data: Iterable[NumberParams]) -> None:
        self.data = data = tuple(data)
        self.by_label = {dif.label: dif for dif in data if dif.label}
        self.indexes = range(IDX_START, len(data) + IDX_START)

    def __iter__(self) -> Iterator[NumberParams]:
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, key: Union[str, int]) -> NumberParams:
        """Return `NumberParams` by given label or index."""
        if isinstance(key, int):
            try:
                index = self.indexes.index(key)
            except ValueError:
                raise IndexError(key) from None
            return self.data[index]
        if isinstance(key, str):
            return self.by_label[key]
        raise TypeError(
            f"Given key have wrong type ({type(key)}). `str` or `int` needed."
        )

    @property
    def labels(self) -> KeysView[str]:
        return self.by_label.keys()


# =========
# selection
# =========


@cli_window("Difficulty Selection")
def difficulty_selection(
        difficulty_container: DifficultyContainer
) -> Difficulty:
    """Difficulty selection.
    Can raise EOFError.
    """
    print(f"\n{difficulty_table(difficulty_container)}\n")

    while True:
        try:
            input_ = prompt(
                "Enter key: ",
                validator=DifficultySelectionValidator(difficulty_container),
                validate_while_typing=False,
            )
        except KeyboardInterrupt:
            continue

        return parse_difficulty_selection(input_, difficulty_container)


@cli_window("Number Parameters Selection")
def number_params_selection(
        number_params_container: NumberParamsContainer,
) -> NumberParams:
    """`NumberParams` selection.
    Can raise EOFError.
    """
    print(f"\n{number_params_table(number_params_container)}\n")

    while True:
        try:
            input_ = prompt(
                "Enter key: ",
                validator=NumberParamsSelectionValidator(number_params_container),
                validate_while_typing=False,
            )
        except KeyboardInterrupt:
            continue

        return parse_number_params_selection(input_, number_params_container)


class DifficultySelectionValidator(Validator):

    def __init__(self, difficulty_container: DifficultyContainer) -> None:
        self.difficulty_container = difficulty_container

    def validate(self, document: Document) -> None:
        try:
            parse_difficulty_selection(document.text, self.difficulty_container)
        except ValueError as err:
            raise ValidationError(
                message="Invalid input",
                cursor_position=document.cursor_position,
            ) from err


class NumberParamsSelectionValidator(Validator):

    def __init__(self, number_params_container: NumberParamsContainer) -> None:
        self.number_params_container = number_params_container

    def validate(self, document: Document) -> None:
        try:
            parse_number_params_selection(document.text, self.number_params_container)
        except ValueError as err:
            raise ValidationError(
                message="Invalid input",
                cursor_position=document.cursor_position,
            ) from err


def parse_difficulty_selection(
        input_: str,
        difficulty_container: DifficultyContainer,
) -> Difficulty:

    if input_.isdigit() and int(input_) in difficulty_container.indexes:
        return difficulty_container[int(input_)]

    if (
            len(splited := input_.split()) == 2
            and all(elem.isdigit() for elem in splited)
            and tuple(map(int, splited)) in difficulty_container.attrs
    ):
        number_size, digits_num = splited
        return difficulty_container[int(number_size), int(digits_num)]

    raise ValueError("Invalid input")


def parse_number_params_selection(
        input_: str,
        number_params_container: NumberParamsContainer,
) -> NumberParams:

    if input_.isdigit() and int(input_) in number_params_container.indexes:
        return number_params_container[int(input_)]

    try:
        return number_params_container[input_]
    except KeyError:
        pass

    raise ValueError("Invalid input")


# ======
# Tables
# ======


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


def difficulty_table(difficulties: DifficultyContainer) -> str:
    return tabulate(
        map(attrgetter("number_size", "digits_num"), difficulties),
        headers=("Key", "Size", "Digits"),
        colalign=("right", "center", "center"),
        showindex=difficulties.indexes,
    )


def number_params_table(number_params_container: NumberParamsContainer) -> str:
    return tabulate(
        map(
            attrgetter("label", "number_size", "digits_description"),
            number_params_container,
        ),
        headers=("Key", "Label", "Size", "Digits"),
        colalign=("right", "left", "center", "center"),
        showindex=number_params_container.indexes,
    )


# ========
# Commands
# ========


COMMAND_PREFIX: Final[str] = "!"


def validate_command(cmd_line: str) -> None:
    """Validate command line string. `COMMAND_PREFIX` have to be removed."""
    shlex.split(cmd_line)


class Command(metaclass=ABCMeta):
    """Command abstract class."""

    shorthand: ClassVar[Optional[str]] = None

    def __init__(self, game: Game) -> None:
        self.game = game
        self.args_range = get_args_lims(self.execute)

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


def get_args_lims(func: Callable) -> Tuple[int, float]:
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
    r[estart] [-l | -i | {number_params_idx} | {number_params_label}]

        Restart the round. If argument is given, change number parameters.

        -l  List number parameters.

        -i  Interactively choose new number parameters.
    """
    name = "restart"
    shorthand = "r"

    def execute(self, arg: str = "") -> None:

        if not arg:
            raise RestartGame

        number_params_container = self.game.number_params_container

        if arg == "-i":
            try:
                number_params = number_params_selection(number_params_container)
            except EOFError:
                return
        elif arg == "-l":
            print(number_params_table(number_params_container))
            return
        else:
            try:
                number_params = parse_number_params_selection(
                        arg, number_params_container
                )
            except IndexError:
                print(f"Invalid key: {arg}")
                return
            except ValueError:
                print(f"No '{arg}' number parameters available")
                return

        raise RestartGame(number_params=number_params)


class HistoryCmd(Command):
    """
    hi[story]

        Show history.
    """

    name = "history"
    shorthand = "hi"

    def execute(self) -> None:

        if self.game.guess_handler.steps_done == 0:
            print("History is empty")
            return

        print(tabulate(
            self.game.guess_handler.history,
            headers=("Number", "Bulls", "Cows"),
            colalign=("center", "center", "center"),
            tablefmt="plain",
        ))


class RankingCmd(Command):
    """
    ra[nking] [{difficulty_idx} | {difficulty_key} | -l]

        Show ranking of given difficulty. If not given directly show
        difficulty selection.

            -l  List available ranking`s difficulties.
    """

    name = "ranking"
    shorthand = "ra"

    def execute(self, arg: str = "") -> None:

        difficulty_container = DifficultyContainer(
            self.game.ranking_repo.available_difficulties()
        )

        if not difficulty_container:
            print("\nEmpty rankings\n")
            return

        if arg == "-l":
            print(difficulty_table(difficulty_container))
            return
        elif arg:
            try:
                difficulty = parse_difficulty_selection(
                    arg, difficulty_container
                )
            except IndexError:
                print(f"Invalid index '{arg}'")
                return
        else:
            try:
                difficulty = difficulty_selection(difficulty_container)
            except EOFError:
                return

        pager(ranking_table(
            self.game.ranking_repo.load(difficulty)
        ))
