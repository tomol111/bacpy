from dataclasses import FrozenInstanceError
import datetime

import pandas as pd
import pytest

import bacpy.core
from bacpy.core import (
    _add_ranking_position,
    available_ranking_difficulties,
    Difficulty,
    DIGITS_RANGE,
    GameException,
    _get_ranking_path,
    load_ranking,
    MIN_NUM_SIZE,
    QuitGame,
    RANKINGS_DIR,
    RestartGame,
    _save_ranking,
    StopPlaying,
)


# ===============
# Game Exceptions
# ===============


def test_base_game_exception():
    assert isinstance(GameException(), Exception)


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
    assert isinstance(exception_cls(), GameException)


def test_restart_game_exception():
    difficulty = Difficulty(3, 5)
    exception = RestartGame(difficulty)
    assert exception.difficulty == difficulty


# =============
# Ranking tools
# =============


def test_get_ranking_path():
    assert _get_ranking_path(Difficulty(3, 5)) == RANKINGS_DIR / f"{3}_{5}.csv"


@pytest.fixture
def tmp_rankings_dir(tmp_path_factory):
    tmp_rankings_dir = tmp_path_factory.mktemp("rankings")
    bacpy.core.RANKINGS_DIR = tmp_rankings_dir
    yield tmp_rankings_dir
    bacpy.core.RANKINGS_DIR = RANKINGS_DIR


def test_save_load_ranking(tmp_rankings_dir):
    difficulty = Difficulty(3, 5)
    ranking = pd.DataFrame(
        [
            (datetime.datetime(2021, 6, 5), 10, "Tomek"),
            (datetime.datetime(2021, 6, 4), 15, "Tomasz"),
        ],
        columns=["datetime", "score", "player"],
    )
    _save_ranking(ranking, difficulty)
    pd.testing.assert_frame_equal(
        load_ranking(difficulty),
        ranking,
    )


def test_load_ranking_not_existing(tmp_rankings_dir):
    expected_empty_ranking = pd.DataFrame(
        columns=["datetime", "score", "player"]
    ).astype({"datetime": "datetime64", "score": int})

    pd.testing.assert_frame_equal(
        load_ranking(Difficulty(3, 5)),
        expected_empty_ranking,
    )


def test_add_ranking_position():
    ranking = pd.DataFrame(
        [
            (datetime.datetime(2021, 6, 5), 10, "Tomek"),
            (datetime.datetime(2021, 6, 4), 15, "Tomasz"),
        ],
        columns=["datetime", "score", "player"],
    )

    expected_ranking = pd.DataFrame(
        [
            (datetime.datetime(2021, 6, 5), 10, "Tomek"),
            (datetime.datetime(2021, 6, 6), 12, "New player"),
            (datetime.datetime(2021, 6, 4), 15, "Tomasz"),
        ],
        columns=["datetime", "score", "player"],
    )

    updated_ranking = _add_ranking_position(
        ranking,
        datetime.datetime(2021, 6, 6),
        12,
        "New player",
    )

    pd.testing.assert_frame_equal(
        updated_ranking.reset_index(drop=True),  # don't check index
        expected_ranking,
    )


def test_add_ranking_position_overflow():
    ranking = pd.DataFrame(
        [
            (datetime.datetime(2021, 3, 17), 6, "Tomasz"),
            (datetime.datetime(2021, 2, 18), 8, "Maciek"),
            (datetime.datetime(2021, 6, 5), 10, "Tomek"),
            (datetime.datetime(2021, 6, 4), 15, "Tomasz"),
            (datetime.datetime(2021, 6, 6), 15, "Zofia"),
            (datetime.datetime(2021, 4, 5), 17, "Piotrek"),
            (datetime.datetime(2020, 12, 30), 20, "Tomasz"),
            (datetime.datetime(2021, 3, 20), 21, "Tomasz"),
            (datetime.datetime(2020, 11, 10), 30, "Darek"),
            (datetime.datetime(2020, 8, 1), 32, "Tomasz"),
        ],
        columns=["datetime", "score", "player"],
    )

    expected_ranking = pd.DataFrame(
        [
            (datetime.datetime(2021, 3, 17), 6, "Tomasz"),
            (datetime.datetime(2021, 2, 18), 8, "Maciek"),
            (datetime.datetime(2021, 6, 5), 10, "Tomek"),
            (datetime.datetime(2021, 6, 6), 12, "New player"),
            (datetime.datetime(2021, 6, 4), 15, "Tomasz"),
            (datetime.datetime(2021, 6, 6), 15, "Zofia"),
            (datetime.datetime(2021, 4, 5), 17, "Piotrek"),
            (datetime.datetime(2020, 12, 30), 20, "Tomasz"),
            (datetime.datetime(2021, 3, 20), 21, "Tomasz"),
            (datetime.datetime(2020, 11, 10), 30, "Darek"),
        ],
        columns=["datetime", "score", "player"],
    )

    updated_ranking = _add_ranking_position(
        ranking,
        datetime.datetime(2021, 6, 6),
        12,
        "New player",
    )

    pd.testing.assert_frame_equal(
        updated_ranking.reset_index(drop=True),  # don't check index
        expected_ranking,
    )


def test_available_ranking_difficulties(tmp_rankings_dir):
    difficulties = [
        Difficulty(3, 5),
        Difficulty(5, 10),
        Difficulty(6, 15),
    ]
    expected_available_difficulties = difficulties[::2]
    for difficulty in expected_available_difficulties:
        _get_ranking_path(difficulty).touch()

    assert list(
        available_ranking_difficulties(difficulties)
    ) == expected_available_difficulties


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
