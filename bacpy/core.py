from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import random
import sys
from typing import (
    FrozenSet,
    Iterable,
    List,
    NamedTuple,
    Optional,
    overload,
    Sequence,
    Tuple,
    TypeVar,
)

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

    def __init__(self, number: str, difficulty: Difficulty) -> None:
        self._number = number
        self._difficulty = difficulty
        assert is_number_valid(difficulty, number)
        self._history: List["GuessingRecord"] = []
        self._finished = False
        self._score_data: Optional[_ScoreData] = None

        if sys.flags.dev_mode:
            print(self._number)

    @property
    def history(self) -> SequenceView[GuessingRecord]:
        return SequenceView(self._history)

    @property
    def steps(self) -> int:
        return len(self._history)

    @property
    def difficulty(self) -> Difficulty:
        return self._difficulty

    @property
    def finished(self) -> bool:
        return self._finished

    @property
    def score_data(self) -> _ScoreData:
        if self._score_data is None:
            raise AttributeError("`score_data` not yet available")
        return self._score_data

    def parse_guess(self, guess: str) -> GuessingRecord:

        if self._finished:
            raise RuntimeError("Round has been finished")
        if not is_number_valid(self._difficulty, guess):
            raise ValueError("Parsed number is invalid")

        bulls, cows = _comput_bullscows(guess, self._number)
        hist_record = GuessingRecord(guess, bulls, cows)
        self._history.append(hist_record)

        if bulls == self.difficulty.num_size:
            self._finished = True
            self._score_data = _ScoreData(
                finish_datetime=datetime.now(),
                difficulty=self.difficulty,
                score=self.steps,
            )

        return hist_record


def draw_number(difficulty: Difficulty) -> str:
    """Draw number valid for given difficulty.

    It used by `RoundCore` but can be used to generate random guesses.
    """
    return "".join(
        random.sample(difficulty.digs_set, difficulty.num_size)
    )


def is_number_valid(difficulty: Difficulty, number: str) -> bool:
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


class GuessingRecord(NamedTuple):
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

    def __eq__(self, other: object) -> bool:
        if isinstance(other, SequenceView):
            return self._data == other._data
        return self._data == other

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._data!r})"


# ============
# Difficulties
# ============


MIN_NUM_SIZE: Final[int] = 3
DIGITS_RANGE: Final[str] = "123456789abcdef"


@dataclass(order=True, frozen=True)
class Difficulty:

    num_size: int
    digs_num: int
    name: str = field(default="", compare=False)

    def __post_init__(self):
        if self.num_size < MIN_NUM_SIZE:
            raise ValueError(
                f"`num_size` ({self.num_size}) smaller than {MIN_NUM_SIZE}"
            )
        if self.num_size >= self.digs_num:
            raise ValueError(
                f"`num_size` ({self.num_size}) not less "
                f"than `digs_num` ({self.digs_num})"
            )
        if self.digs_num > len(DIGITS_RANGE):
            raise ValueError(
                f"`digs_num` ({self.digs_num}) over {len(DIGITS_RANGE)}"
            )

    @property
    def digs_set(self) -> FrozenSet[str]:
        return frozenset(DIGITS_RANGE[:self.digs_num])

    @property
    def digs_range(self) -> str:
        if MIN_NUM_SIZE <= self.digs_num <= 9:
            return f"1-{self.digs_num}"
        if self.digs_num == 10:
            return "1-9,a"
        if 11 <= self.digs_num <= len(DIGITS_RANGE):
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


# ===============
# Game Exceptions
# ===============


class GameException(Exception):
    """Base game exception class."""


class QuitGame(GameException):
    """Quit game exception."""


class StopPlaying(GameException):
    """Stop playing exception."""


class RestartGame(GameException):
    """Restart game exception."""
    def __init__(self, difficulty: Difficulty = None):
        self.difficulty = difficulty


# =============
# Ranking tools
# =============


class _RankingRecord(NamedTuple):
    score: int
    dt: datetime
    player: str


class Ranking:

    def __init__(
            self,
            data: Iterable[_RankingRecord],
            difficulty: Difficulty,
    ) -> None:
        self._data = sorted(data)
        self._difficulty = difficulty

    @property
    def data(self) -> SequenceView[_RankingRecord]:
        return SequenceView(self._data)

    @property
    def difficulty(self) -> Difficulty:
        return self._difficulty

    def add(self, record: _RankingRecord) -> None:
        self._data.append(record)
        self._data.sort()
        self._data = self._data[:RANKING_SIZE]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Ranking):
            return NotImplemented
        return (
            self.difficulty == other.difficulty
            and self.data == other.data
        )


class _ScoreData(NamedTuple):
    """Data that can be used to save score."""
    finish_datetime: datetime
    difficulty: Difficulty
    score: int


class RankingManager:

    def __init__(self, rankings_dir: Path) -> None:
        self._rankings_dir = rankings_dir

    def _get_path(self, difficulty: Difficulty) -> Path:
        return (
            self._rankings_dir
            / f"{difficulty.num_size}_{difficulty.digs_num}.csv"
        )

    def _save(
            self,
            ranking: Ranking,
    ) -> None:
        path = self._get_path(ranking.difficulty)
        with open(path, "w") as file:
            writer = csv.writer(file)
            writer.writerows(ranking.data)

    def load(self, difficulty: Difficulty) -> Ranking:
        """Read and return ranking by given difficulty.

        If ranking is not available return empty one.
        """
        path = self._get_path(difficulty)
        path.touch()
        with open(path, "r") as file:
            return Ranking(
                data=(
                    _RankingRecord(
                        int(score),
                        datetime.fromisoformat(dt),
                        player,
                    )
                    for score, dt, player in csv.reader(file)
                ),
                difficulty=difficulty,
            )

    def is_not_empty(self, difficulty: Difficulty) -> bool:
        path = self._get_path(difficulty)
        return path.exists() and bool(path.stat().st_size)

    def is_score_fit_into(self, score_data: _ScoreData) -> bool:
        ranking = self.load(score_data.difficulty)
        return (
            len(ranking.data) < RANKING_SIZE
            or ranking.data[-1].score > score_data.score
        )

    def update(
            self,
            score_data: _ScoreData,
            player: str,
    ) -> Ranking:
        ranking = self.load(score_data.difficulty)
        ranking.add(
            _RankingRecord(
                score_data.score,
                score_data.finish_datetime,
                player,
            )
        )
        self._save(ranking)
        return ranking
