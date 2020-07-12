"""BacPy - Bulls and Cows game implementation by Tomasz Olszewski"""


__version__ = '0.3'
__author__ = 'Tomasz Olszewski'


from collections import Counter
from contextvars import ContextVar
from datetime import datetime
import os
from pathlib import Path
import random
import subprocess
import sys
from textwrap import dedent
from typing import (Callable, ClassVar, Collection, Dict, Set, Iterable,
                    Iterator, List, NoReturn, Optional, Union, Tuple, TypeVar)

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
DIF_INDEX_START = 1

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


class Difficulty:
    name_: str
    digs_set: Set[str]
    digs_range: str
    num_size: int
    digs_num: int


class DifficultyContainer:
    """Keeps available difficulties.

    Uses DIF_INDEX_START to handle index.
    """

    def __init__(self) -> None:
        self._difs = pd.DataFrame(
            [['easy', set('123456'), '1-6', 3],
             ['normal', set('123456789'), '1-9', 4],
             ['hard', set('123456789abcdf'), '1-9a-f', 5]],
            columns=['name_', 'digs_set', 'digs_range', 'num_size'],
        )
        self._difs['digs_num'] = self._difs['digs_set'].map(len)
        # self._difs.sort_values(by=['digs_num', 'num_size'], inplace=True)
        self._difs.index = pd.RangeIndex(DIF_INDEX_START,
                                         len(self._difs) + DIF_INDEX_START)

    def __iter__(self) -> Iterator[Difficulty]:
        return iter(self._difs)

    def __len__(self) -> int:
        return len(self._difs)

    def __getitem__(self, key: Union[str, int]) -> Difficulty:
        """Return Difficulty by given name or index."""
        if isinstance(key, int):
            return self._difs.loc[key]
        if isinstance(key, str):
            return self._difs[self._difs['name_'] == key].iloc[0]
        return

    def __contains__(self, name: object) -> bool:
        """Return True if given name is available."""
        return name in list(self._difs['name_'])

    def isindex(self, number: int) -> bool:
        """Return True if given number is available index."""
        return number in self._difs.index

    def table(self) -> pd.DataFrame:
        """pd.DataFrame containing difficulties` 'name_', 'num_size'
        and 'digs_range'."""
        return self._difs[['name_', 'num_size', 'digs_range']]

    def get(self, key: Union[str, int], default: Optional[T] = None) \
            -> Union[Difficulty, Optional[T]]:
        """Return difficulty for key. If key don't exist return 'default.

        Key can be 'name_' or index number.
        """
        try:
            item = self[key]
        except KeyError:
            return default
        else:
            return item


# =======
# History
# =======


class History:
    """Keep history of the Round."""

    def __init__(self) -> None:
        self._hist = pd.DataFrame(columns=['number', 'bulls', 'cows'],
                                  index=pd.Index([], name='step'))

    def __iter__(self) -> Iterator[Tuple[int, pd.Series]]:
        return self._hist.iterrows()

    def __len__(self) -> int:
        return len(self._hist)

    def append(self, number: str, bulls: int, cows: int) -> None:
        self._hist.loc[len(self)+1] = number, bulls, cows

    def table(self) -> pd.DataFrame:
        return self._hist


# ======
# Events
# ======


class GameEvent(Exception):
    """Base game event class."""


class QuitGame(GameEvent):
    """Quit game event."""


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


class Command:
    """Command abstract class and commands manager."""

    PREFIX: ClassVar[str] = '!'
    instances: ClassVar[List['Command']] = []

    doc: Optional[str]
    name: str
    shorthand: str
    splitlines: bool = True

    def __init__(self, cmdfunc: Callable[..., None], **kwargs: T) -> None:
        self.instances.append(self)
        self._cmdfunc = cmdfunc
        for attrname, variable in kwargs.items():
            setattr(self, attrname, variable)
        if not hasattr(self, 'name'):
            self.name = cmdfunc.__name__
        if not hasattr(self, 'doc'):
            self.doc = cmdfunc.__doc__

    def __call__(self, args: str = '') -> None:
        if args:
            self._cmdfunc(*args.split() if self.splitlines else args)
        else:
            self._cmdfunc()

    @classmethod
    def add(cls, **kwargs: T) -> Callable[[Callable[..., None]], 'Command']:
        def decorator(cmdfunc):
            return cls(cmdfunc, **kwargs)
        return decorator


class CommandContainer(Collection[Command], Iterable[Command]):
    """Contain Command objects and allows execute them."""

    def __init__(self) -> None:
        self._cmds: Dict[str, Command] = \
            {cmd.name: cmd for cmd in Command.instances}
        self._shorthands_map: Dict[str, str] = \
            {cmd.shorthand: cmd.name for cmd in Command.instances}

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

    def get(self, key: str, default: Optional[T] = None) \
            -> Union[Command, Optional[T]]:
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
            name, *largs = input_.split(maxsplit=1)
            if name in self:
                args = largs[0] if largs else ''
                try:
                    self[name](args)
                except (CommandError, TypeError) as err:
                    print(err)
                return
        print(
            "  Type '!help' to show game help or '!help commands' ",
            "  to show help about available commands",
            sep='\n',
        )


@Command.add(name='help', shorthand='h', splitlines=False)
def help_cmd(arg: str = '') -> None:
    """!h[elp] [{subject}]

    Show help about {subject}. When {subject} is not parsed show game help.
    """

    if not arg:
        pager(GAME_HELP)
        return

    commands = get_game().commands
    if arg == 'commands':
        pager('\n'.join([cmd.doc for cmd in commands
                         if cmd.doc is not None]))
        return

    if arg in commands:
        cmd = commands[arg]
        if cmd.doc is not None:
            print(cmd.doc)
        else:
            print(f"  Command {cmd} don't have documentation")
        return

    raise CommandError(f"  No help for '{arg}'")


@Command.add(name='quit', shorthand='q')
def quit_cmd() -> NoReturn:
    """!q[uit]

    Stop playing.
    """
    raise QuitGame


@Command.add(name='exit', shorthand='e')
def exit_cmd() -> NoReturn:
    """!q[uit]

    Exit the game.
    """
    sys.exit()


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
        print(tabulate(game.difs.table(),
                       headers=('Key', 'Difficulty', 'Size', 'Digits'),
                       tablefmt='plain'))
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
    print(tabulate(game.round.history.table(),
                   headers=('Number', 'Bulls', 'Cows'),
                   colalign=('center', 'center', 'center'),
                   showindex=False,
                   tablefmt='plain'))


# ====================
# Difficulty selection
# ====================


def diff_selection_validator_func(text: str) -> bool:
    return text.isdigit() and get_game().difs.isindex(int(text))


diff_selection_validator = Validator.from_callable(
    diff_selection_validator_func,
    error_message='Invalid key',
    move_cursor_to_end=True,
)


def difficulty_selection() -> Difficulty:
    """Difficulty selection."""
    difficulties = get_game().difs
    table = tabulate(difficulties.table(),
                     headers=('Key', 'Difficulty', 'Size', 'Digits'),
                     colalign=('right', 'left', 'center', 'center'))

    # Compute table width
    fnlp = table.find('\n')
    width = table.find('\n', fnlp+1) - fnlp - 1

    print(' Difficulty selection '.center(width, '='))
    print('\n', table, '\n', sep='')
    try:
        while True:
            try:
                input_ = prompt('Enter key: ',
                                validator=diff_selection_validator,
                                validate_while_typing=False).strip()
            except EOFError:
                raise CancelOperation
            except KeyboardInterrupt:
                continue

            try:
                difficulty = difficulties[int(input_)]
            except (ValueError, IndexError):
                continue
            else:
                return difficulty
    finally:
        print(''.center(width, '='))


# =====
# Round
# =====


class RoundValidator(Validator):

    def validate(self, document: Document) -> None:
        input_: str = document.text.strip()

        difficulty = get_game().round.difficulty
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

    def __init__(self, difficulty: Difficulty) -> None:
        self._difficulty = difficulty
        self.history = History()

        self._draw_number()
        if sys.flags.dev_mode:
            print(self._number)

    def _draw_number(self) -> None:
        """Draw number digits from self.difficulty.digs_set."""
        self._number = ''.join(
            random.sample(self.difficulty.digs_set, self.difficulty.num_size)
        )

    @property
    def steps(self) -> int:
        return len(self.history)

    @property
    def difficulty(self) -> Difficulty:
        return self._difficulty

    @property
    def toolbar(self) -> str:
        return ("  |  ".join([f" Difficulty: {self.difficulty.name_}",
                              f"Size: {self.difficulty.num_size}",
                              f"Digits: {self.difficulty.digs_range}"]))

    def run(self) -> History:
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

                if bulls == self.difficulty.num_size:
                    print(f"\n *** You guessed in {self.steps} steps ***")
                    return self.history

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


# ============
# Menu actions
# ============


MenuAction = Callable[[], None]


def menu_selection_validator_func(text: str) -> bool:
    return text.isdigit() and int(text) in get_game().actions


menu_selection_validator = Validator.from_callable(
    menu_selection_validator_func,
    error_message='Invalid key',
    move_cursor_to_end=True,
)


def menu_selecton() -> MenuAction:
    actions = get_game().actions
    table = tabulate(actions.table(),
                     headers=('Key', 'Action'),
                     colalign=('left', 'right'))

    # Compute table width
    fnlp = table.find('\n')
    width = table.find('\n', fnlp+1) - fnlp - 1

    print(' Menu '.center(width, '='))
    print('\n', table, '\n', sep='')
    try:
        while True:
            try:
                input_ = prompt('Enter key: ',
                                validator=menu_selection_validator,
                                validate_while_typing=False).strip()
            except EOFError:
                sys.exit()
            except KeyboardInterrupt:
                continue

            try:
                action = actions[int(input_)]
            except (ValueError, IndexError):
                continue
            else:
                return action
    finally:
        print(''.center(width, '='))


# TODO: extend player_validator
player_validator = Validator.from_callable(
    lambda text: 2 < len(text.strip()) < 10,
    error_message="Invalid player name",
    move_cursor_to_end=True,
)


def play_action() -> None:
    try:
        difficulty = difficulty_selection()
    except CancelOperation:
        return

    game = get_game()
    player = ''
    while True:
        try:
            game.round = Round(difficulty)
            history = game.round.run()
        except RestartGame as rg:
            if rg.difficulty is not None:
                difficulty = rg.difficulty
            continue
        except QuitGame:
            return
        finally:
            del game.round

        while True:
            try:
                input_ = prompt('Save score as: ',
                                default=player,
                                validator=player_validator,
                                validate_while_typing=False).strip()
            except EOFError:
                break
            except KeyboardInterrupt:
                player = ''
                continue

            player = input_
            try:
                if ask_ok(f'Confirm player: "{player}" [Y/n] '):
                    Path('.scores.csv').touch()
                    scores = pd.read_csv(
                        '.scores.csv',
                        names=['datetime', 'posible_digits',
                               'number_size', 'score', 'player'],
                        parse_dates=['datetime'],
                    )

                    dtindex = datetime.now()
                    scores.loc[len(scores)] = (
                        dtindex,
                        difficulty.digs_num,
                        difficulty.num_size,
                        len(history),
                        player,
                    )

                    scores.to_csv('.scores.csv', header=False, index=False)

                    scores = (
                        scores
                        [(scores['posible_digits'] == difficulty.digs_num)
                         & (scores['number_size'] == difficulty.num_size)]
                        .sort_values(by=['score', 'datetime'])
                        .head(10)
                    )

                    if dtindex in list(scores['datetime']):
                        scores = (
                            scores
                            [['score', 'player']]
                            .astype({'score': object, 'player': object})
                            .reset_index(drop=True)
                            .join(pd.Series(range(1, 11), name='pos.'),
                                  how='outer')
                            .set_index('pos.')
                            .fillna('-')
                        )

                        pager(tabulate(scores,
                                       headers='keys',
                                       colalign=('left', 'center', 'left')))

                    break

            except CancelOperation:
                break

        try:
            if ask_ok('Do you want to continue? [Y/n]: '):
                continue
            else:
                return
        except CancelOperation:
            return


def help_action() -> None:
    pager(GAME_HELP)


def show_ranking() -> None:
    Path('.scores.csv').touch()
    scores = pd.read_csv(
        '.scores.csv',
        names=['datetime', 'posible_digits',
               'number_size', 'score', 'player'],
        parse_dates=['datetime'],
    )

    grouped = scores.groupby(['posible_digits', 'number_size'])
    data = pd.DataFrame(
        [[key, pos_digs, num_size]
         for key, (pos_digs, num_size) in enumerate(grouped.groups, start=1)],
        columns=['Key', 'Digits', 'Size'],
    ).set_index('Key')

    table = tabulate(data,
                     headers='keys',
                     colalign=('left', 'center', 'center'))

    # Compute table width
    fnlp = table.find('\n')
    width = table.find('\n', fnlp+1) - fnlp - 1

    print(' Show ranking '.center(width, '='))
    print('\n', table, '\n', sep='')
    try:
        while True:
            try:
                input_ = prompt('Enter key: ',
                                validator=menu_selection_validator,
                                validate_while_typing=False).strip()
            except EOFError:
                return
            except KeyboardInterrupt:
                continue

            try:
                digssize = tuple(data.loc[int(input_)])
            except (ValueError, IndexError):
                continue
            else:
                scores = (grouped.get_group(digssize)
                                 .sort_values(by=['score', 'datetime']))

                scores = (
                    scores
                    [['score', 'player']]
                    .head(10).astype({'score': object, 'player': object})
                    .reset_index(drop=True)
                    .join(pd.Series(range(1, 11), name='pos.'), how='outer')
                    .set_index('pos.')
                    .fillna('-')
                )

                pager(tabulate(scores,
                               headers='keys',
                               colalign=('left', 'center', 'left')))
    finally:
        print(''.center(width, '='))


class ActionContainer:
    """Contain Command objects and allows execute them."""

    def __init__(self) -> None:
        self._actions = pd.DataFrame(
            [['Play', play_action],
             ['Show rankings', show_ranking],
             ['Show help', help_action],
             ['EXIT', sys.exit]],
            columns=['label', 'action'],
            index=[1, 2, 3, 0],
        )

    def __getitem__(self, key: int) -> MenuAction:
        """Give Command by given name or shorthand."""
        if isinstance(key, int):
            return self._actions.loc[key].action
        raise IndexError(key)

    def __contains__(self, item: T) -> bool:
        if isinstance(item, int):
            return item in self._actions.index
        return False

    def table(self) -> pd.DataFrame:
        return self._actions[['label']].copy()


# ====
# Game
# ====


_current_game: ContextVar = ContextVar('game')


class Game:
    """Game class."""

    GAME_START = dedent(f"""
        ==================================
        ----------- BacPy v{__version__} -----------
        ==================================
    """)

    def __new__(cls) -> 'Game':
        if _current_game.get(None) is None:
            instance = super(Game, cls).__new__(cls)
            _current_game.set(instance)
        else:
            raise TypeError(
                f"Can't create more than 1 instance of '{cls.__name__}' class")
        return instance

    def __init__(self) -> None:
        self.difs = DifficultyContainer()
        self.commands = CommandContainer()
        self.actions = ActionContainer()

        self.round: Round

    def run(self) -> None:
        """Runs game loop."""
        print(self.GAME_START)
        while True:
            action = menu_selecton()
            action()


def get_game() -> Game:
    return _current_game.get()


if __name__ == '__main__':
    Game().run()
