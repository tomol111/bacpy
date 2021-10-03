from __future__ import annotations

from abc import ABCMeta, abstractmethod
from collections import Counter
import csv
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import random
import sys
from typing import (
    FrozenSet,
    Generator,
    Iterator,
    List,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
)

from bacpy.utils import SequenceView

if sys.version_info >= (3, 8):
    from typing import Final, final
else:
    from typing_extensions import Final, final


# Constants
PLAYER_NAME_LEN_LIMS: Final[Tuple[int, int]] = (3, 20)
RANKINGS_DIR: Final[Path] = Path(".rankings")
RANKING_SIZE: Final[int] = 10


# =====
# Round
# =====


@final
class RoundCore(Generator[Tuple[int, int], str, None]):

    def __init__(self, number: str, difficulty: Difficulty) -> None:
        self._number = number
        self._difficulty = difficulty
        assert is_number_valid(number, difficulty)
        self._history: List[GuessRecord] = []
        self._closed = False
        self._score_data: Optional[_ScoreData] = None

    @property
    def history(self) -> SequenceView[GuessRecord]:
        return SequenceView(self._history)

    @property
    def steps(self) -> int:
        return len(self._history)

    @property
    def difficulty(self) -> Difficulty:
        return self._difficulty

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def score_data(self) -> _ScoreData:
        if self._score_data is None:
            raise AttributeError("`score_data` not available")
        return self._score_data

    def send(self, guess: str) -> Tuple[int, int]:

        if self._closed:
            raise StopIteration

        assert is_number_valid(guess, self._difficulty)

        bulls, cows = _bullscows(guess, self._number)
        self._history.append(GuessRecord(guess, bulls, cows))

        if guess == self._number:
            self._score_data = _ScoreData(
                score=self.steps,
                dt=datetime.now(),
                difficulty=self.difficulty.to_simple(),
            )
            self.throw(StopIteration)

        return bulls, cows

    def throw(self, typ, val=None, tb=None):
        self._closed = True
        super().throw(typ, val, tb)


def draw_number(difficulty: Difficulty) -> str:
    return "".join(
        random.sample(difficulty.digs_set, difficulty.num_size)
    )


def is_number_valid(number: str, difficulty: Difficulty) -> bool:
    try:
        validate_number(number, difficulty)
    except ValueError:
        return False
    else:
        return True


def validate_number(number: str, difficulty: Difficulty) -> None:

    wrong_chars = set(number) - difficulty.digs_set
    if wrong_chars:
        raise ValueError(
            "Wrong characters: "
            + ", ".join(f"'{char}'" for char in wrong_chars)
        )

    if len(number) != difficulty.num_size:
        raise ValueError(
            f"Number have {len(number)} digits. {difficulty.num_size} needed",
        )

    rep_digits = {digit for digit, count in Counter(number).items() if count > 1}
    if rep_digits:
        raise ValueError(
            "Repeated digits: "
            + ", ".join(f"'{digit}'" for digit in rep_digits)
        )


def _bullscows(guess: str, number: str) -> Tuple[int, int]:
    bulls, cows = 0, 0

    for guess_char, number_char in zip(guess, number):
        if guess_char == number_char:
            bulls += 1
        elif guess_char in number:
            cows += 1

    return bulls, cows


class GuessRecord(NamedTuple):
    number: str
    bulls: int
    cows: int


# ============
# Difficulties
# ============


MIN_NUM_SIZE: Final[int] = 3
DIGITS_RANGE: Final[str] = "123456789abcdefghijklmnopqrstuvwxyz"


@dataclass(order=True, frozen=True)
class SimpleDifficulty:

    num_size: int
    digs_num: int

    def __post_init__(self):
        if self.num_size < MIN_NUM_SIZE:
            raise ValueError(
                f"`num_size` ({self.num_size}) smaller than `MIN_NUM_SIZE`"
                f" ({MIN_NUM_SIZE})"
            )
        if self.num_size >= self.digs_num:
            raise ValueError(
                f"`num_size` ({self.num_size}) not less than `digs_num`"
                f" ({self.digs_num})"
            )


def default_digs_set(digs_num: int) -> FrozenSet[str]:
    _validate_digs_num_for_defaults(digs_num)
    return frozenset(DIGITS_RANGE[:digs_num])


def default_digs_label(digs_num: int) -> str:
    _validate_digs_num_for_defaults(digs_num)
    if digs_num <= 9:
        return f"1-{digs_num}"
    elif digs_num == 10:
        return "1-9,a"
    else:
        return f"1-9,a-{DIGITS_RANGE[digs_num - 1]}"


def _validate_digs_num_for_defaults(digs_num: int) -> None:
    if digs_num < MIN_NUM_SIZE:
        raise ValueError(
            f"`digs_num` ({digs_num}) less than `MIN_NUM_SIZE`"
            f" ({MIN_NUM_SIZE})"
        )
    if digs_num > len(DIGITS_RANGE):
        raise ValueError(
            f"`digs_num` ({digs_num}) over length of `DIGITS_RANGE`"
            f" ({len(DIGITS_RANGE)})"
        )


@dataclass(order=True, frozen=True)
class Difficulty(SimpleDifficulty):

    digs_set: FrozenSet[str] = field(compare=False)
    digs_label: str = field(compare=False)
    name: str = field(default="", compare=False)

    @classmethod
    def new_default(
            cls,
            num_size: int,
            digs_num: int,
            name: str = "",
    ) -> Difficulty:
        digs_set = default_digs_set(digs_num)
        digs_label = default_digs_label(digs_num)
        return cls(num_size, digs_num, digs_set, digs_label, name)

    def __post_init__(self):
        super().__post_init__()
        if self.digs_num != len(self.digs_set):
            raise ValueError(
                f"`digs_num` ({self.digs_num}) is diffrent from length of"
                f" `digs_set` ({len(self.digs_set)})"
            )

    def to_simple(self) -> SimpleDifficulty:
        return SimpleDifficulty(self.num_size, self.digs_num)


DEFAULT_DIFFICULTIES: Final[Tuple[Difficulty, ...]] = tuple(
    Difficulty.new_default(num_size, digs_num, name)
    for num_size, digs_num, name in (
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


@dataclass(frozen=True)
class Ranking:
    # Be aware that comparing different kind of sequences can return false
    # even if they contain same elements.
    data: Sequence[_RankingRecord]
    difficulty: SimpleDifficulty


class _ScoreData(NamedTuple):
    """Data that can be used to save score."""
    score: int
    dt: datetime
    difficulty: SimpleDifficulty


class RankingManager(metaclass=ABCMeta):

    @abstractmethod
    def load(self, difficulty: SimpleDifficulty) -> Ranking:
        """Read and return ranking.
        If ranking is not available return empty one.
        """
        return Ranking((), difficulty)

    @abstractmethod
    def update(
            self,
            score_data: _ScoreData,
            player: str,
    ) -> Ranking:
        """Add new record to ranking. Save and return updated one."""
        assert is_player_name_valid(player)
        ranking = self.load(score_data.difficulty)
        new_data = list(ranking.data)
        new_data.append(
            _RankingRecord(
                score_data.score,
                score_data.dt,
                player,
            ),
        )
        new_data.sort()
        return Ranking(tuple(new_data[:RANKING_SIZE]), ranking.difficulty)

    @abstractmethod
    def available_difficulties(self) -> Iterator[SimpleDifficulty]:
        """Yields `SimpleDifficulty` for each available and not empty ranking."""
        return
        yield

    def is_score_fit_into(self, score_data: _ScoreData) -> bool:
        ranking = self.load(score_data.difficulty)
        return (
            len(ranking.data) < RANKING_SIZE
            or ranking.data[-1].score > score_data.score
        )


class FileRankingManager(RankingManager):

    def __init__(self, rankings_dir: Path) -> None:
        self._rankings_dir = rankings_dir

    def load(self, difficulty: SimpleDifficulty) -> Ranking:
        path = self._get_path(difficulty)
        path.touch()
        with open(path, "r") as file:
            return Ranking(
                data=tuple(
                    _RankingRecord(
                        int(score),
                        datetime.fromisoformat(dt),
                        player,
                    )
                    for score, dt, player in csv.reader(file)
                ),
                difficulty=difficulty,
            )

    def update(
            self,
            score_data: _ScoreData,
            player: str,
    ) -> Ranking:
        updated_ranking = super().update(score_data, player)
        self._save(updated_ranking)
        return updated_ranking

    def _save(
            self,
            ranking: Ranking,
    ) -> None:
        path = self._get_path(ranking.difficulty)
        with open(path, "w") as file:
            writer = csv.writer(file)
            writer.writerows(ranking.data)

    def _get_path(self, difficulty: SimpleDifficulty) -> Path:
        return (
            self._rankings_dir
            / f"{difficulty.num_size}_{difficulty.digs_num}.csv"
        )

    def available_difficulties(self) -> Iterator[SimpleDifficulty]:
        for path in self._rankings_dir.iterdir():
            if path.stat().st_size:
                num_size, digs_num = map(int, path.stem.split("_"))
                yield SimpleDifficulty(num_size, digs_num)


def is_player_name_valid(name: str) -> bool:
    """Wraps `validate_player_name()` for assertion and testing purposes."""
    try:
        validate_player_name(name)
    except ValueError:
        return False
    else:
        return True


def validate_player_name(name: str) -> None:
    min_len, max_len = PLAYER_NAME_LEN_LIMS
    if len(name) < min_len:
        raise ValueError(
            f"Too short name ({len(name)}). At least {min_len} characters needed."
        )
    if len(name) > max_len:
        raise ValueError(
            f"Too long name ({len(name)}). Maximum {max_len} characters allowed."
        )
