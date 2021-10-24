from __future__ import annotations

from abc import ABCMeta, abstractmethod
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
import random
from typing import (
    Callable,
    Final,
    FrozenSet,
    Generator,
    Iterator,
    List,
    NamedTuple,
    Optional,
    Tuple,
)

from bacpy.utils import SequenceView


# Constants
PLAYER_NAME_LEN_LIMS: Final[Tuple[int, int]] = (3, 20)


# =====
# Round
# =====


class GuessHandler(Generator[Tuple[int, int], str, None]):

    def __init__(self, secret_number: str, number_params: NumberParams) -> None:
        assert is_number_valid(secret_number, number_params)
        self._secret_number = secret_number
        self._number_params = number_params
        self._history: List[GuessRecord] = []
        self._closed = False
        self._score_data: Optional[ScoreData] = None

    @property
    def history(self) -> SequenceView[GuessRecord]:
        return SequenceView(self._history)

    @property
    def steps_done(self) -> int:
        return len(self._history)

    @property
    def number_params(self) -> NumberParams:
        return self._number_params

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def score_data(self) -> ScoreData:
        if self._score_data is None:
            raise AttributeError("`score_data` not available")
        return self._score_data

    def send(self, guess: str) -> Tuple[int, int]:

        if self._closed:
            raise StopIteration

        assert is_number_valid(guess, self._number_params)

        bulls, cows = self._bullscows(guess, self._secret_number)
        self._history.append(GuessRecord(guess, bulls, cows))

        if guess == self._secret_number:
            self._score_data = ScoreData(
                score=self.steps_done,
                dt=datetime.now(),
                difficulty=self.number_params.difficulty,
            )
            self.throw(StopIteration)

        return bulls, cows

    @staticmethod
    def _bullscows(guess: str, secret_number: str) -> Tuple[int, int]:
        bulls, cows = 0, 0
        for guess_char, number_char in zip(guess, secret_number):
            if guess_char == number_char:
                bulls += 1
            elif guess_char in secret_number:
                cows += 1
        return bulls, cows

    def throw(self, typ, val=None, tb=None):
        self._closed = True
        super().throw(typ, val, tb)


def draw_number(number_params: NumberParams) -> str:
    return "".join(
        random.sample(number_params.digits_set, number_params.number_size)
    )


def is_number_valid(number: str, number_params: NumberParams) -> bool:
    try:
        validate_number(number, number_params)
    except ValueError:
        return False
    else:
        return True


def validate_number(number: str, number_params: NumberParams) -> None:

    wrong_chars = set(number) - number_params.digits_set
    if wrong_chars:
        raise ValueError(
            "Wrong characters: "
            + ", ".join(f"'{char}'" for char in wrong_chars)
        )

    if len(number) != number_params.number_size:
        raise ValueError(
            f"Number have {len(number)} digits. {number_params.number_size} needed",
        )

    rep_digits = {digit for digit, count in Counter(number).items() if count > 1}
    if rep_digits:
        raise ValueError(
            "Repeated digits: "
            + ", ".join(f"'{digit}'" for digit in rep_digits)
        )


class GuessRecord(NamedTuple):
    number: str
    bulls: int
    cows: int


# ==========
# Difficulty
# ==========


MIN_NUM_SIZE: Final[int] = 3


@dataclass(order=True, frozen=True)
class Difficulty:

    number_size: int
    digits_num: int

    def __post_init__(self):
        if self.number_size < MIN_NUM_SIZE:
            raise ValueError(
                f"`number_size` ({self.number_size}) smaller than `MIN_NUM_SIZE`"
                f" ({MIN_NUM_SIZE})"
            )
        if self.number_size >= self.digits_num:
            raise ValueError(
                f"`number_size` ({self.number_size}) not less than `digits_num`"
                f" ({self.digits_num})"
            )


# ======
# Digits
# ======


@dataclass(frozen=True)
class Digits:
    """Contain digits that can be in number and short description to be
    displayed on a screan.
    """
    data: FrozenSet[str]
    description: str


DigitsFactory = Callable[[int], Digits]


def standard_digits(digits_num: int) -> Digits:
    DIGITS_SEQUENCE = "123456789abcdefghijklmnopqrstuvwxyz"

    if digits_num < 2:
        raise ValueError(
            f"`digits_num` less than 2 ({digits_num})"
        )
    if digits_num > len(DIGITS_SEQUENCE):
        raise ValueError(
            f"`digits_num` grater than {len(DIGITS_SEQUENCE)} ({digits_num})"
        )

    digits_set = frozenset(DIGITS_SEQUENCE[:digits_num])

    if digits_num <= 9:
        description = f"[1-{digits_num}]"
    elif digits_num == 10:
        description = "[1-9a]"
    else:
        description = f"[1-9a-{DIGITS_SEQUENCE[digits_num - 1]}]"

    return Digits(digits_set, description)


# ============
# NumberParams
# ============


@dataclass(order=True, frozen=True)
class NumberParams:

    difficulty: Difficulty
    digits_set: FrozenSet[str] = field(compare=False)
    digits_description: str = field(compare=False)
    label: str = field(compare=False, default="")

    def __post_init__(self):
        if self.digits_num != len(self.digits_set):
            raise ValueError(
                f"`digits_num` ({self.digits_num}) is diffrent from length of"
                f" `digits_set` ({len(self.digits_set)})"
            )

    @property
    def number_size(self) -> int:
        return self.difficulty.number_size

    @property
    def digits_num(self) -> int:
        return self.difficulty.digits_num

    @classmethod
    def from_digits_factory(
            cls,
            difficulty: Difficulty,
            digits_factory: DigitsFactory,
            label: str = "",
    ) -> NumberParams:
        digits = digits_factory(difficulty.digits_num)
        return cls(difficulty, digits.data, digits.description, label)

    @classmethod
    def standard(cls, difficulty: Difficulty, label: str = "") -> NumberParams:
        return cls.from_digits_factory(difficulty, standard_digits, label)


DEFAULT_NUMBER_PARAMETERS: Final[Tuple[NumberParams, ...]] = tuple(
    NumberParams.standard(difficulty, label)
    for difficulty, label in (
        (Difficulty(3, 6), "easy"),
        (Difficulty(4, 9), "normal"),
        (Difficulty(5, 15), "hard"),
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


@dataclass
class RestartGame(GameException):
    """Restart game exception."""
    number_params: Optional[NumberParams] = None


# =============
# Ranking tools
# =============


RANKING_SIZE: Final[int] = 10


@dataclass(frozen=True)
class Ranking:
    data: Tuple[RankingRecord, ...]
    difficulty: Difficulty


class RankingRecord(NamedTuple):
    score: int
    dt: datetime
    player: str


class ScoreData(NamedTuple):
    """Data that can be used to save score."""
    score: int
    dt: datetime
    difficulty: Difficulty


class RankingRepo(metaclass=ABCMeta):

    @abstractmethod
    def load(self, difficulty: Difficulty) -> Ranking:
        """Read and return ranking.
        If ranking is not available return empty one.
        """
        return Ranking((), difficulty)

    @abstractmethod
    def update(
            self,
            score_data: ScoreData,
            player: str,
    ) -> Ranking:
        """Add new record to ranking. Save and return updated one."""
        assert is_player_name_valid(player)
        ranking = self.load(score_data.difficulty)
        new_data = list(ranking.data)
        new_data.append(
            RankingRecord(
                score_data.score,
                score_data.dt,
                player,
            ),
        )
        new_data.sort()
        return Ranking(tuple(new_data[:RANKING_SIZE]), ranking.difficulty)

    @abstractmethod
    def available_difficulties(self) -> Iterator[Difficulty]:
        """Yields `Difficulty` for each available and not empty ranking."""
        return
        yield

    def is_score_fit_into(self, score_data: ScoreData) -> bool:
        ranking = self.load(score_data.difficulty)
        return (
            len(ranking.data) < RANKING_SIZE
            or ranking.data[-1].score > score_data.score
        )


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
