from dataclasses import FrozenInstanceError
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from bacpy.core import (
    _comput_bullscows,
    Difficulty,
    DIGITS_RANGE,
    draw_number,
    GameException,
    GuessingRecord,
    is_number_valid,
    MIN_NUM_SIZE,
    QuitGame,
    RankingManager,
    RANKING_SIZE,
    RestartGame,
    RoundCore,
    SequenceView,
    _ScoreData,
    StopPlaying,
)


# ===============
# Game Exceptions
# ===============


@pytest.mark.parametrize(
    "exception_cls",
    (
        GameException,
        QuitGame,
        StopPlaying,
        RestartGame,
    )
)
def test_game_exceptions(exception_cls):
    with pytest.raises(GameException):
        raise exception_cls


def test_restart_game_exception():
    difficulty = Difficulty(3, 5)
    exception = RestartGame(difficulty)
    assert exception.difficulty == difficulty


# =============
# Ranking tools
# =============


# _ScoreData
# ----------


def test_score_data_as_tuple():
    score_data = _ScoreData(
        datetime(2021, 6, 5),
        Difficulty(3, 5),
        10,
    )
    assert isinstance(score_data, tuple)


def test_score_data_as_namespace():
    finish_datetime = datetime(2021, 6, 5)
    difficulty = Difficulty(3, 5)
    score = 10
    score_data = _ScoreData(
        finish_datetime=finish_datetime,
        difficulty=difficulty,
        score=score,
    )
    assert score_data.finish_datetime == finish_datetime
    assert score_data.difficulty == difficulty
    assert score_data.score == score


# RankingManager
# --------------


def test_ranking_manager_get_path():
    path = Path("some_dir")
    assert RankingManager(path)._get_path(
        Difficulty(3, 5)
    ) == path / "3_5.csv"


def test_ranking_manager_save_load_unitarity(tmp_path):
    ranking_manager = RankingManager(tmp_path)
    difficulty = Difficulty(3, 5)
    ranking = pd.DataFrame(
        [
            (datetime(2021, 6, 5), 10, "Tomek"),
            (datetime(2021, 6, 4), 15, "Tomasz"),
        ],
        columns=["datetime", "score", "player"],
    )
    ranking_manager._save(ranking, difficulty)
    pd.testing.assert_frame_equal(
        ranking_manager.load(difficulty),
        ranking,
    )


def test_ranking_manager_load_not_existing_ranking(tmp_path):
    ranking_manager = RankingManager(tmp_path)
    difficulty = Difficulty(3, 5)
    expected_empty_ranking = pd.DataFrame(
        columns=["datetime", "score", "player"]
    ).astype({"datetime": "datetime64", "score": int})

    pd.testing.assert_frame_equal(
        ranking_manager.load(difficulty),
        expected_empty_ranking,
    )
    assert ranking_manager._get_path(difficulty).exists()


def test_ranking_manager_is_not_empty(tmp_path):
    difficulty = Difficulty(3, 5)
    ranking_manager = RankingManager(tmp_path)

    assert not ranking_manager.is_not_empty(difficulty)

    ranking_manager._get_path(difficulty).touch()
    assert not ranking_manager.is_not_empty(difficulty)

    ranking_manager._save(
        pd.DataFrame(
            [(datetime(2021, 6, 5), 10, "Tomek")],
            columns=["datetime", "score", "player"],
        ),
        difficulty,
    )
    assert ranking_manager.is_not_empty(difficulty)


def test_ranking_manager_is_score_fit_into_not_full(tmp_path):
    difficulty = Difficulty(3, 5)
    ranking_manager = RankingManager(tmp_path)
    ranking = pd.DataFrame(
        [
            (datetime(2021, 6, 5), 10, "Tomek"),
            (datetime(2021, 6, 4), 15, "Tomasz"),
        ],
        columns=["datetime", "score", "player"],
    )
    ranking_manager._save(ranking, difficulty)
    assert ranking_manager.is_score_fit_into(
        _ScoreData(datetime(2021, 6, 6), difficulty, 12)
    )
    assert ranking_manager.is_score_fit_into(
        _ScoreData(datetime(2021, 6, 7), difficulty, 16)
    )


def test_ranking_manager_is_score_fit_into_full(tmp_path):
    assert RANKING_SIZE == 10, "Ranking size changed"
    difficulty = Difficulty(3, 5)
    ranking_manager = RankingManager(tmp_path)
    ranking = pd.DataFrame(
        [
            (datetime(2021, 3, 17), 6, "Tomasz"),
            (datetime(2021, 2, 18), 8, "Maciek"),
            (datetime(2021, 6, 5), 10, "Tomek"),
            (datetime(2021, 6, 4), 15, "Tomasz"),
            (datetime(2021, 6, 6), 15, "Zofia"),
            (datetime(2021, 4, 5), 17, "Piotrek"),
            (datetime(2020, 12, 30), 20, "Tomasz"),
            (datetime(2021, 3, 20), 21, "Tomasz"),
            (datetime(2020, 11, 10), 30, "Darek"),
            (datetime(2020, 8, 1), 32, "Tomasz"),
        ],
        columns=["datetime", "score", "player"],
    )
    ranking_manager._save(ranking, difficulty)

    assert ranking_manager.is_score_fit_into(
        _ScoreData(datetime(2021, 6, 6), difficulty, 12)
    )
    assert not ranking_manager.is_score_fit_into(
        _ScoreData(datetime(2021, 6, 6), difficulty, 33)
    )


def test_ranking_mamager_update_not_full(tmp_path):
    difficulty = Difficulty(3, 5)
    ranking_manager = RankingManager(tmp_path)
    ranking = pd.DataFrame(
        [
            (datetime(2021, 6, 5), 10, "Tomek"),
            (datetime(2021, 6, 4), 15, "Tomasz"),
        ],
        columns=["datetime", "score", "player"],
    )
    ranking_manager._save(ranking, difficulty)
    expected_ranking = pd.DataFrame(
        [
            (datetime(2021, 6, 5), 10, "Tomek"),
            (datetime(2021, 6, 6), 12, "New player"),
            (datetime(2021, 6, 4), 15, "Tomasz"),
        ],
        columns=["datetime", "score", "player"],
    )
    score_data = _ScoreData(datetime(2021, 6, 6), difficulty, 12)

    updated_ranking = (
        ranking_manager
        .update(score_data, "New player")
        .reset_index(drop=True)  # don't check index
    )

    pd.testing.assert_frame_equal(updated_ranking, expected_ranking)
    pd.testing.assert_frame_equal(
        updated_ranking,
        ranking_manager.load(difficulty),
    )


def test_ranking_mamager_update_full(tmp_path):
    difficulty = Difficulty(3, 5)
    ranking_manager = RankingManager(tmp_path)
    ranking = pd.DataFrame(
        [
            (datetime(2021, 3, 17), 6, "Tomasz"),
            (datetime(2021, 2, 18), 8, "Maciek"),
            (datetime(2021, 6, 5), 10, "Tomek"),
            (datetime(2021, 6, 4), 15, "Tomasz"),
            (datetime(2021, 6, 6), 15, "Zofia"),
            (datetime(2021, 4, 5), 17, "Piotrek"),
            (datetime(2020, 12, 30), 20, "Tomasz"),
            (datetime(2021, 3, 20), 21, "Tomasz"),
            (datetime(2020, 11, 10), 30, "Darek"),
            (datetime(2020, 8, 1), 32, "Tomasz"),
        ],
        columns=["datetime", "score", "player"],
    )
    ranking_manager._save(ranking, difficulty)
    expected_ranking = pd.DataFrame(
        [
            (datetime(2021, 3, 17), 6, "Tomasz"),
            (datetime(2021, 2, 18), 8, "Maciek"),
            (datetime(2021, 6, 5), 10, "Tomek"),
            (datetime(2021, 6, 6), 12, "New player"),
            (datetime(2021, 6, 4), 15, "Tomasz"),
            (datetime(2021, 6, 6), 15, "Zofia"),
            (datetime(2021, 4, 5), 17, "Piotrek"),
            (datetime(2020, 12, 30), 20, "Tomasz"),
            (datetime(2021, 3, 20), 21, "Tomasz"),
            (datetime(2020, 11, 10), 30, "Darek"),
        ],
        columns=["datetime", "score", "player"],
    )
    score_data = _ScoreData(datetime(2021, 6, 6), difficulty, 12)

    updated_ranking = (
        ranking_manager
        .update(score_data, "New player")
    )

    pd.testing.assert_frame_equal(updated_ranking, expected_ranking)
    pd.testing.assert_frame_equal(
        updated_ranking,
        ranking_manager.load(difficulty),
    )


def test_ranking_mamager_update_overflow(tmp_path):
    difficulty = Difficulty(3, 5)
    ranking_manager = RankingManager(tmp_path)
    ranking = pd.DataFrame(
        [
            (datetime(2021, 3, 17), 6, "Tomasz"),
            (datetime(2021, 2, 18), 8, "Maciek"),
            (datetime(2021, 6, 5), 10, "Tomek"),
            (datetime(2021, 6, 4), 15, "Tomasz"),
            (datetime(2021, 6, 6), 15, "Zofia"),
            (datetime(2021, 4, 5), 17, "Piotrek"),
            (datetime(2020, 12, 30), 20, "Tomasz"),
            (datetime(2021, 3, 20), 21, "Tomasz"),
            (datetime(2020, 11, 10), 30, "Darek"),
            (datetime(2020, 8, 1), 32, "Tomasz"),
        ],
        columns=["datetime", "score", "player"],
    )
    ranking_manager._save(ranking, difficulty)
    score_data = _ScoreData(datetime(2021, 6, 6), difficulty, 35)

    updated_ranking = (
        ranking_manager
        .update(score_data, "New player")
    )

    pd.testing.assert_frame_equal(updated_ranking, ranking)
    pd.testing.assert_frame_equal(
        updated_ranking,
        ranking_manager.load(difficulty),
    )


# ============
# Difficulties
# ============


def test_difficulty_init():
    difficulty = Difficulty(3, 6, "name_str")
    assert difficulty.num_size == 3
    assert difficulty.digs_num == 6
    assert difficulty.name == "name_str"
    assert difficulty.digs_set == set("123456")
    assert difficulty.digs_range == "1-6"


def test_difficulty_repr():
    assert repr(Difficulty(3, 6, "name_str")) == (
        "Difficulty(num_size=3, digs_num=6, name='name_str')"
    )


def test_difficulty_frozen():
    with pytest.raises(FrozenInstanceError):
        Difficulty(3, 5).num_size = 12


@pytest.mark.parametrize(
    ("num_size", "digs_num"),
    (
        (6, 6),  # num_size == digs_num
        (7, 5),  # num_size > digs_num
        (MIN_NUM_SIZE - 1, 5),
        (3, len(DIGITS_RANGE) + 1),
    ),
)
def test_difficulty_not_valid(num_size, digs_num):
    with pytest.raises(ValueError):
        Difficulty(num_size, digs_num)


@pytest.mark.parametrize(
    ("digs_num", "expected"),
    (
        (8, "1-8"),
        (10, "1-9,a"),
        (13, "1-9,a-d"),
    ),
)
def test_difficulty_digs_range(digs_num, expected):
    assert Difficulty(3, digs_num).digs_range == expected


def test_difficulty_comparing():
    assert Difficulty(3, 5, "a") == Difficulty(3, 5, "b")


def test_difficulty_sorting():
    difficulties = [
        Difficulty(5, 10, "abcd"),
        Difficulty(6, 10),
        Difficulty(3, 5),
    ]
    assert sorted(difficulties) == [
        Difficulty(3, 5),
        Difficulty(5, 10, "abcd"),
        Difficulty(6, 10),
    ]


# ============
# SequenceView
# ============


# Sequence methods
# ----------------


def test_sequence_view_contains():
    sequence = SequenceView([1, 2, 3])
    assert 1 in sequence
    assert 4 not in sequence


def test_sequence_view_len():
    sequence = SequenceView([1, 2, 3])
    assert len(sequence) == 3


def test_sequence_view_getitem():
    sequence = SequenceView([1, 2, 3])
    assert sequence[1] == 2
    assert sequence[-1] == 3
    with pytest.raises(IndexError):
        sequence[3]


def test_sequence_view_slicing():
    sequence = SequenceView([1, 2, 3])
    assert sequence[:2] == [1, 2]
    assert sequence[::2] == [1, 3]
    assert sequence[:] == [1, 2, 3]


def test_sequence_view_iter():
    lst = [1, 2, 3]
    sequence = SequenceView(lst)
    assert all(
        left == right
        for left, right in zip(sequence, lst)
    )


def test_sequence_view_reversed():
    lst = [1, 2, 3]
    sequence = SequenceView(lst)
    assert all(
        left == right
        for left, right in zip(reversed(sequence), reversed(lst))
    )


def test_sequence_view_bool():
    assert not SequenceView([])
    assert SequenceView([1, 2, 3])


def test_sequence_view_index():
    sequence = SequenceView([1, 2, 3])
    assert sequence.index(2) == 1
    with pytest.raises(ValueError):
        sequence.index(4)


def test_sequence_view_count():
    sequence = SequenceView([1, 2, 3, 2, 2])
    assert sequence.count(1) == 1
    assert sequence.count(2) == 3
    assert sequence.count(4) == 0


# Other features
# --------------


def test_sequence_view_immutability():
    sequence = SequenceView([1, 2, 3])
    with pytest.raises(TypeError):
        sequence[0] = 10
    with pytest.raises(TypeError):
        del sequence[1]


def test_sequence_view_repr():
    assert repr(SequenceView([1, 2, 3])) == "SequenceView([1, 2, 3])"
    assert repr(SequenceView(range(3))) == "SequenceView(range(0, 3))"


def test_sequence_view_dynamic_view():
    lst = [1, 2, 3]
    sequence = SequenceView(lst)
    lst.append(object())
    assert all(
        left is right
        for left, right in zip(sequence, lst)
    )


# =====
# Round
# =====


# GuessingRecord
# --------------


def test_guessing_record_as_tuple():
    tple = ("1234", 2, 1)
    record = GuessingRecord(*tple)
    assert record == tple


def test_guessing_record_unpacking():
    tple = ("1234", 2, 1)
    number, bulls, cows = GuessingRecord(*tple)
    assert (number, bulls, cows) == tple


def test_guessint_record_as_namespace():
    record = GuessingRecord(number="1234", bulls=2, cows=1)
    assert record.number == "1234"
    assert record.bulls == 2
    assert record.cows == 1


# _comput_bullscows
# -----------------


@pytest.mark.parametrize(
    ("guess", "number", "bulls", "cows"),
    (
        ("1234", "1234", 4, 0),
        ("4321", "1234", 0, 4),
        ("3214", "1234", 2, 2),
        ("5678", "1234", 0, 0),
    )
)
def test_compute_bullscows(guess, number, bulls, cows):
    assert _comput_bullscows(guess, number) == (bulls, cows)


# is_number_valid
# ---------------


@pytest.mark.parametrize(
    ("difficulty", "number"),
    (
        (Difficulty(3, 6), "163"),
        (Difficulty(4, 9), "1593"),
        (Difficulty(5, 15), "2f5a9"),
    )
)
def test_is_number_valid(difficulty, number):
    assert is_number_valid(difficulty, number)


@pytest.mark.parametrize(
    ("difficulty", "number"),
    (
        (Difficulty(3, 6), "301"),
        (Difficulty(4, 9), "51a9"),
        (Difficulty(5, 15), "1g4a8"),
    )
)
def test_is_number_valid_wrong_characters(difficulty, number):
    assert not is_number_valid(difficulty, number)


@pytest.mark.parametrize(
    ("difficulty", "number"),
    (
        (Difficulty(3, 5), "1234"),
        (Difficulty(3, 5), "34"),
        (Difficulty(4, 9), "12349"),
        (Difficulty(4, 9), "31"),
        (Difficulty(5, 15), "12f3a49b"),
        (Difficulty(5, 15), "31d"),
    )
)
def test_is_number_valid_wrong_length(difficulty, number):
    assert not is_number_valid(difficulty, number)


@pytest.mark.parametrize(
    ("difficulty", "number"),
    (
        (Difficulty(3, 5), "232"),
        (Difficulty(4, 9), "3727"),
        (Difficulty(5, 15), "3b5b8"),
    )
)
def test_is_number_valid_not_unique_characters(difficulty, number):
    assert not is_number_valid(difficulty, number)


# draw_number
# -----------


@pytest.mark.parametrize(
    "difficulty",
    (
        Difficulty(3, 5),
        Difficulty(4, 9),
        Difficulty(5, 15),
    )
)
def test_draw_number(difficulty):
    number = draw_number(difficulty)
    assert is_number_valid(difficulty, number)


# RoundCore
# ---------


def test_round_core():
    difficulty = Difficulty(3, 5)
    round_core = RoundCore(difficulty)
    number = round_core._number

    # After initiation
    assert is_number_valid(difficulty, number)
    assert round_core.difficulty == difficulty
    assert not round_core.history
    assert not round_core.steps
    assert not round_core.finished
    with pytest.raises(RuntimeError):
        round_core.get_score_data()

    # invalid number
    with pytest.raises(ValueError):
        round_core.parse_guess("")
    assert not round_core.history
    assert not round_core.steps

    # first step
    guess_record_0 = round_core.parse_guess(
        get_other_number(number, difficulty)
    )
    assert isinstance(guess_record_0, GuessingRecord)
    assert round_core.history[0] == guess_record_0
    assert round_core.steps == 1

    # second step
    guess_record_1 = round_core.parse_guess(
        get_other_number(number, difficulty)
    )
    assert round_core.history[0] == guess_record_0
    assert round_core.history[1] == guess_record_1
    assert round_core.steps == 2

    # succesive guess
    guess_record_last = round_core.parse_guess(number)
    assert guess_record_last.bulls == difficulty.num_size
    assert guess_record_last.cows == 0
    assert round_core.steps == 3
    assert round_core.finished

    # finished
    with pytest.raises(RuntimeError):
        round_core.parse_guess(number)
    score_data = round_core.get_score_data()
    assert score_data.finish_datetime
    assert score_data.difficulty == difficulty
    assert score_data.score == 3

    # score data available once
    with pytest.raises(RuntimeError):
        round_core.get_score_data()


def get_other_number(number: str, difficulty: Difficulty) -> str:
    while True:
        other = draw_number(difficulty)
        if other != number:
            return other
