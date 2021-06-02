from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import random
import sys
from typing import (
    FrozenSet,
    Iterable,
    Iterator,
    List,
    NamedTuple,
    overload,
    Sequence,
    Tuple,
    TypeVar,
)

import pandas as pd

if sys.version_info >= (3, 8):
    from typing import Final, final
else:
    from typing_extensions import Final, final


# Type variables
T_co = TypeVar("T_co", covariant=True)


# Constants
PLAYER_NAME_LIMS: Tuple[int, int] = (3, 20)
RANKINGS_DIR: Final[Path] = Path(".rankings")
RANKING_SIZE: Final[int] = 10


# =====
# Round
# =====


@final
class RoundCore:
    """Round core class."""

    def __init__(self, difficulty: "Difficulty") -> None:
        self._difficulty = difficulty
        self._history: List["HistRecord"] = []
        self._number = draw_number(difficulty)
        self._finished = False

        if sys.flags.dev_mode:
            print(self._number)

    @property
    def history(self) -> "SequenceView[HistRecord]":
        return SequenceView(self._history)

    @property
    def steps(self) -> int:
        return len(self._history)

    @property
    def difficulty(self) -> "Difficulty":
        return self._difficulty

    @property
    def finished(self) -> bool:
        return self._finished

    def parse_guess(self, guess: str) -> "HistRecord":

        if self._finished:
            raise RuntimeError("Can't parse guess when round is finished")
        if not is_number_valid(self._difficulty, guess):
            raise ValueError("Parsed number is invalid")

        bulls, cows = _comput_bullscows(guess, self._number)
        hist_record = HistRecord(guess, bulls, cows)
        self._history.append(hist_record)

        if bulls == self.difficulty.num_size:
            self._finished = True
            self._finish_datetime = datetime.now()
            self._ranking = ranking = load_ranking(self._difficulty)
            self._score_fit_in = (
                len(ranking) < RANKING_SIZE
                or ranking.score.iat[-1] > self.steps
            )

        return hist_record

    @property
    def score_fit_in(self) -> bool:
        return self._score_fit_in

    def update_ranking(self, player: str) -> pd.DataFrame:
        """If round has been finished and score fit into ranking update,
        save and return ranking.
        """
        if not self._finished:
            raise RuntimeError("Round not finished yet")
        if not self._score_fit_in:
            raise RuntimeError("Score don't fit into ranking")

        ranking = _add_ranking_position(
            self._ranking,
            self._finish_datetime,
            self.steps,
            player,
        )
        _save_ranking(ranking, self._difficulty)
        return ranking


def draw_number(difficulty: "Difficulty") -> str:
    """Draw number valid for given difficulty.

    It used by `RoundCore` but can be used to generate random guesses.
    """
    return "".join(
        random.sample(difficulty.digs_set, difficulty.num_size)
    )


def is_number_valid(difficulty: "Difficulty", number: str) -> bool:
    """Quick check if number is valid for given difficulty."""
    return (
        not set(number) - difficulty.digs_set  # wrong characters
        and len(number) == difficulty.num_size  # correct length
        and len(set(number)) == len(number)  # unique characters
    )


def _comput_bullscows(guess: str, number: str) -> Tuple[int, int]:
    """Return bulls and cows for given input."""
    bulls, cows = 0, 0

    for guess_char, number_char in zip(guess, number):
        if guess_char == number_char:
            bulls += 1
        elif guess_char in number:
            cows += 1

    return bulls, cows


class HistRecord(NamedTuple):
    """History record of passed guess and the corresponding bulls and cows.
    """
    number: str
    bulls: int
    cows: int


# ============
# SequenceView
# ============


class SequenceView(Sequence[T_co]):

    def __init__(self, data: Sequence[T_co]) -> None:
        self._data = data

    @overload
    def __getitem__(self, index: int) -> T_co: ...

    @overload
    def __getitem__(self, index: slice) -> Sequence[T_co]: ...

    def __getitem__(self, index):
        return self._data[index]

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._data})"


# ============
# Difficulties
# ============


DIGITS_RANGE: Final[str] = "123456789abcdef"


@dataclass(order=True, frozen=True)
class Difficulty:

    num_size: int
    digs_num: int
    name: str = field(default="", compare=False)

    @property
    def digs_set(self) -> FrozenSet[str]:
        return frozenset(DIGITS_RANGE[:self.digs_num])

    @property
    def digs_range(self) -> str:
        if 3 <= self.digs_num <= 9:
            return f"1-{self.digs_num}"
        if self.digs_num == 10:
            return "1-9,a"
        if 11 <= self.digs_num <= 15:
            return f"1-9,a-{DIGITS_RANGE[self.digs_num-1]}"
        raise AttributeError


DEFAULT_DIFFICULTIES: Final[Tuple[Difficulty, ...]] = tuple(
    Difficulty(*args)
    for args in (
        (3, 6, "easy"),
        (4, 9, "normal"),
        (5, 15, "hard"),
    )
)


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
    def __init__(self, difficulty: "Difficulty" = None):
        self.difficulty = difficulty


# =============
# Ranking tools
# =============


def available_ranking_difficulties(
        difficulties: Iterable[Difficulty],
) -> Iterator[Difficulty]:
    """Filter difficulties by the fact that corresponding ranking is
    available.
    """
    for difficulty in difficulties:
        if _get_ranking_path(difficulty).exists():
            yield difficulty


def load_ranking(difficulty: Difficulty) -> pd.DataFrame:
    """Read and return ranking by given difficulty."""
    path = _get_ranking_path(difficulty)
    path.touch()
    return pd.read_csv(
        path,
        names=["datetime", "score", "player"],
        parse_dates=["datetime"],
    )


def _add_ranking_position(
        ranking: pd.DataFrame,
        finish_datetime: datetime,
        score: int,
        player: str,
        *,
        ranking_size: int = RANKING_SIZE,
) -> pd.DataFrame:
    return (
        ranking
        .append(
            {"datetime": finish_datetime, "score": score, "player": player},
            ignore_index=True,
        )
        .sort_values(by=["score", "datetime"])
        .head(ranking_size)
    )


def _save_ranking(ranking: pd.DataFrame, difficulty: Difficulty) -> None:
    ranking.to_csv(
        _get_ranking_path(difficulty),
        header=False,
        index=False,
    )


def _get_ranking_path(difficulty: Difficulty) -> Path:
    return (
        RANKINGS_DIR
        / f"{difficulty.digs_num}_{difficulty.num_size}.csv"
    )
