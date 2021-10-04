from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from bacpy.core import (
    _bullscows,
    default_digs_label,
    default_digs_set,
    Difficulty,
    DIGITS_RANGE,
    draw_number,
    FileRankingManager,
    is_number_valid,
    is_player_name_valid,
    MIN_NUM_SIZE,
    Ranking,
    _RankingRecord,
    RoundCore,
    _ScoreData,
    SimpleDifficulty,
    _validate_digs_num_for_defaults,
)


# =============
# Ranking tools
# =============


# FileRankingManager
# --------------


# TODO: test backward compatibility by snapshotting file


def test_FileRankingManager_load__not_existing_ranking(tmp_path):
    ranking_manager = FileRankingManager(tmp_path)
    difficulty = SimpleDifficulty(4, 6)
    assert ranking_manager.load(difficulty) == Ranking((), difficulty)


def test_FileRankingManager_is_score_fit_into__not_full(tmp_path):
    difficulty = SimpleDifficulty(3, 6)
    ranking_manager = FileRankingManager(tmp_path)

    for score_data, player in (
            (_ScoreData(10, datetime(2021, 6, 5), difficulty), "Tomek"),
            (_ScoreData(15, datetime(2021, 6, 4), difficulty), "Tomasz"),
    ):
        ranking_manager.update(score_data, player)

    assert ranking_manager.is_score_fit_into(
        _ScoreData(12, datetime(2021, 6, 6), difficulty)
    )
    assert ranking_manager.is_score_fit_into(
        _ScoreData(16, datetime(2021, 6, 7), difficulty)
    )


def test_FileRankingManager_is_score_fit_into__full(tmp_path):
    difficulty = SimpleDifficulty(3, 6)
    ranking_manager = FileRankingManager(tmp_path)

    for score_data, player in (
            (_ScoreData(6, datetime(2021, 3, 17), difficulty), "Tomasz"),
            (_ScoreData(8, datetime(2021, 2, 18), difficulty), "Maciek"),
            (_ScoreData(10, datetime(2021, 6, 5), difficulty), "Tomek"),
            (_ScoreData(15, datetime(2021, 6, 4), difficulty), "Tomasz"),
            (_ScoreData(15, datetime(2021, 6, 6), difficulty), "Zofia"),
            (_ScoreData(17, datetime(2021, 4, 5), difficulty), "Piotrek"),
            (_ScoreData(20, datetime(2020, 12, 30), difficulty), "Tomasz"),
            (_ScoreData(21, datetime(2021, 3, 20), difficulty), "Tomasz"),
            (_ScoreData(30, datetime(2020, 11, 10), difficulty), "Darek"),
            (_ScoreData(32, datetime(2020, 8, 1), difficulty), "Tomasz"),
    ):
        ranking_manager.update(score_data, player)

    assert ranking_manager.is_score_fit_into(
        _ScoreData(12, datetime(2021, 6, 6), difficulty)
    )
    assert not ranking_manager.is_score_fit_into(
        _ScoreData(33, datetime(2021, 6, 6), difficulty)
    )


def test_FlieRankingManager_update__not_full(tmp_path):
    difficulty = SimpleDifficulty(5, 8)
    ranking_manager = FileRankingManager(tmp_path)

    for score_data, player in (
            (_ScoreData(15, datetime(2021, 6, 4), difficulty), "Tomasz"),
            (_ScoreData(10, datetime(2021, 6, 5), difficulty), "Tomek"),
            (_ScoreData(12, datetime(2021, 6, 6), difficulty), "Maciek"),
    ):
        updated_ranking = ranking_manager.update(score_data, player)

    expected_ranking = Ranking(
        (
            (10, datetime(2021, 6, 5), "Tomek"),
            (12, datetime(2021, 6, 6), "Maciek"),
            (15, datetime(2021, 6, 4), "Tomasz"),
        ),
        difficulty,
    )

    assert updated_ranking == expected_ranking
    assert updated_ranking == ranking_manager.load(difficulty)


def test_FileRankingMamager_update__full(tmp_path):
    difficulty = SimpleDifficulty(3, 6)
    ranking_manager = FileRankingManager(tmp_path)

    for score_data, player in (
            (_ScoreData(32, datetime(2020, 8, 1), difficulty), "TO_DROP"),
            (_ScoreData(30, datetime(2020, 11, 10), difficulty), "Darek"),
            (_ScoreData(20, datetime(2020, 12, 30), difficulty), "Tomasz"),
            (_ScoreData(6, datetime(2021, 3, 17), difficulty), "Tomasz"),
            (_ScoreData(8, datetime(2021, 2, 18), difficulty), "Maciek"),
            (_ScoreData(10, datetime(2021, 6, 5), difficulty), "Tomek"),
            (_ScoreData(15, datetime(2021, 6, 4), difficulty), "Tomasz"),
            (_ScoreData(15, datetime(2021, 6, 6), difficulty), "Zofia"),
            (_ScoreData(17, datetime(2021, 4, 5), difficulty), "Piotrek"),
            (_ScoreData(21, datetime(2021, 3, 20), difficulty), "Tomasz"),
            (_ScoreData(12, datetime(2021, 6, 6), difficulty), "NEWEST")
    ):
        updated_ranking = ranking_manager.update(score_data, player)

    expected_ranking = Ranking(
        (
            _RankingRecord(6, datetime(2021, 3, 17), "Tomasz"),
            _RankingRecord(8, datetime(2021, 2, 18), "Maciek"),
            _RankingRecord(10, datetime(2021, 6, 5), "Tomek"),
            _RankingRecord(12, datetime(2021, 6, 6), "NEWEST"),
            _RankingRecord(15, datetime(2021, 6, 4), "Tomasz"),
            _RankingRecord(15, datetime(2021, 6, 6), "Zofia"),
            _RankingRecord(17, datetime(2021, 4, 5), "Piotrek"),
            _RankingRecord(20, datetime(2020, 12, 30), "Tomasz"),
            _RankingRecord(21, datetime(2021, 3, 20), "Tomasz"),
            _RankingRecord(30, datetime(2020, 11, 10), "Darek"),
        ),
        difficulty,
    )

    assert updated_ranking == expected_ranking
    assert updated_ranking == ranking_manager.load(difficulty)


def test_FlieRankingManager_update__overflow(tmp_path):
    difficulty = SimpleDifficulty(3, 6)
    ranking_manager = FileRankingManager(tmp_path)

    for score_data, player in (
            (_ScoreData(32, datetime(2020, 8, 1), difficulty), "Tomek"),
            (_ScoreData(30, datetime(2020, 11, 10), difficulty), "Darek"),
            (_ScoreData(20, datetime(2020, 12, 30), difficulty), "Tomasz"),
            (_ScoreData(6, datetime(2021, 3, 17), difficulty), "Tomasz"),
            (_ScoreData(8, datetime(2021, 2, 18), difficulty), "Maciek"),
            (_ScoreData(10, datetime(2021, 6, 5), difficulty), "Tomek"),
            (_ScoreData(15, datetime(2021, 6, 4), difficulty), "Tomasz"),
            (_ScoreData(15, datetime(2021, 6, 6), difficulty), "Zofia"),
            (_ScoreData(17, datetime(2021, 4, 5), difficulty), "Piotrek"),
            (_ScoreData(21, datetime(2021, 3, 20), difficulty), "Tomasz"),
            (_ScoreData(35, datetime(2021, 6, 6), difficulty), "NEWEST")
    ):
        updated_ranking = ranking_manager.update(score_data, player)

    expected_ranking = Ranking(
        (
            _RankingRecord(6, datetime(2021, 3, 17), "Tomasz"),
            _RankingRecord(8, datetime(2021, 2, 18), "Maciek"),
            _RankingRecord(10, datetime(2021, 6, 5), "Tomek"),
            _RankingRecord(15, datetime(2021, 6, 4), "Tomasz"),
            _RankingRecord(15, datetime(2021, 6, 6), "Zofia"),
            _RankingRecord(17, datetime(2021, 4, 5), "Piotrek"),
            _RankingRecord(20, datetime(2020, 12, 30), "Tomasz"),
            _RankingRecord(21, datetime(2021, 3, 20), "Tomasz"),
            _RankingRecord(30, datetime(2020, 11, 10), "Darek"),
            _RankingRecord(32, datetime(2020, 8, 1), "Tomek"),
        ),
        difficulty,
    )

    assert updated_ranking == expected_ranking
    assert updated_ranking == ranking_manager.load(difficulty)


def test_FlieRankingManager_available_difficulties(tmp_path):
    difficulty1 = SimpleDifficulty(4, 8)
    difficulty2 = SimpleDifficulty(4, 10)
    difficulty3 = SimpleDifficulty(3, 5)
    ranking_manager = FileRankingManager(tmp_path)
    ranking_manager.load(difficulty1)
    ranking_manager.update(
        _ScoreData(10, datetime(2020, 12, 30), difficulty2), "Tomek"
    )
    ranking_manager.update(
        _ScoreData(7, datetime(2021, 4, 10), difficulty2), "Maciek"
    )
    ranking_manager.update(
        _ScoreData(5, datetime(2021, 3, 2), difficulty3), "Piotrek"
    )
    assert (
        set(ranking_manager.available_difficulties())
        == {difficulty2, difficulty3}
    )


# is_player_name_valid
# --------------------

@pytest.mark.parametrize(
    "name",
    ("abc", "abcdefghijk", "abcdefghijklmnopqrst")
)
def test_validate_player_name_pass(name):
    assert is_player_name_valid(name)


@pytest.mark.parametrize(
    "name",
    ("", "ab", "abcdefghijklmnopqrstu", "abcdefghijklmnopqrstuvwxyz")
)
def test_validate_player_name_exception(name):
    assert not is_player_name_valid(name)


# ============
# Difficulties
# ============


def test_simple_difficulty_init():
    num_size = 3
    digs_num = 6
    difficulty = SimpleDifficulty(num_size, digs_num)
    assert difficulty.num_size == num_size
    assert difficulty.digs_num == digs_num


@pytest.mark.parametrize(
    ("num_size", "digs_num"),
    (
        (6, 6),  # num_size == digs_num
        (7, 5),  # num_size > digs_num
        (MIN_NUM_SIZE - 1, 5),
    ),
)
def test_simple_difficulty_not_valid(num_size, digs_num):
    with pytest.raises(ValueError):
        SimpleDifficulty(num_size, digs_num)


def test_simple_difficulty_eq():
    assert (
        SimpleDifficulty(3, 6)
        == SimpleDifficulty(3, 6)
    )


def test_simple_difficulty_ne():
    assert (
        SimpleDifficulty(3, 6)
        != SimpleDifficulty(3, 7)
    )


def test_simple_difficulty_ordering():
    difficulties = [
        SimpleDifficulty(5, 10),
        SimpleDifficulty(6, 10),
        SimpleDifficulty(3, 6),
    ]
    assert sorted(difficulties) == [
        SimpleDifficulty(3, 6),
        SimpleDifficulty(5, 10),
        SimpleDifficulty(6, 10),
    ]


def test_simple_difficulty_frozen():
    difficulty = SimpleDifficulty(3, 6)
    with pytest.raises(FrozenInstanceError):
        del difficulty.num_size


@pytest.mark.parametrize(
    "digs_num",
    (
        MIN_NUM_SIZE,
        MIN_NUM_SIZE + 3,
        len(DIGITS_RANGE),
        len(DIGITS_RANGE) - 3,
    ),
)
def test_validate_digs_num_for_defaults_valid(digs_num):
    _validate_digs_num_for_defaults(digs_num)


@pytest.mark.parametrize(
    "digs_num",
    (
        MIN_NUM_SIZE - 1,
        MIN_NUM_SIZE - 2,
        len(DIGITS_RANGE) + 1,
        len(DIGITS_RANGE) + 3,
    ),
)
def test_validate_digs_num_for_defaults_not_valid(digs_num):
    with pytest.raises(ValueError):
        _validate_digs_num_for_defaults(digs_num)


@pytest.mark.parametrize(
    ("digs_num", "digits"),
    (
        (4, "1234"),
        (8, "12345678"),
        (10, "123456789a"),
        (13, "123456789abcd"),
        (35, "123456789abcdefghijklmnopqrstuvwxyz"),
    ),
)
def test_default_digs_set(digs_num, digits):
    assert default_digs_set(digs_num) == frozenset(digits)


@pytest.mark.parametrize(
    ("digs_num", "expected"),
    (
        (4, "1-4"),
        (8, "1-8"),
        (10, "1-9,a"),
        (13, "1-9,a-d"),
        (35, "1-9,a-z"),
    ),
)
def test_default_digs_label(digs_num, expected):
    assert default_digs_label(digs_num) == expected


@pytest.mark.parametrize(
    "digs_num",
    (
        MIN_NUM_SIZE - 1,
        len(DIGITS_RANGE) + 1,
    ),
)
def test_default_validation(digs_num):
    with pytest.raises(ValueError):
        default_digs_set(digs_num)
    with pytest.raises(ValueError):
        default_digs_label(digs_num)


def test_difficulty_inheritance():
    assert issubclass(Difficulty, SimpleDifficulty)


def test_difficulty_init():
    num_size = 3
    digs_num = 6
    digs_set = frozenset("123456")
    digs_label = "1-6"
    name = "name_str"
    difficulty = Difficulty(num_size, digs_num, digs_set, digs_label, name)
    assert difficulty.num_size == num_size
    assert difficulty.digs_num == digs_num
    assert difficulty.digs_set == digs_set
    assert difficulty.digs_label == digs_label
    assert difficulty.name == name


def test_difficulty_new_default():
    difficulty = Difficulty.new_default(3, 6, "some name")
    assert difficulty.num_size == 3
    assert difficulty.digs_num == 6
    assert difficulty.digs_set == frozenset("123456")
    assert difficulty.digs_label == "1-6"
    assert difficulty.name == "some name"


@pytest.mark.parametrize(
    ("num_size", "digs_num", "digs", "digs_label"),
    (
        (6, 6, "123456", "1-6"),  # num_size == digs_num
        (7, 5, "12345", "1-5"),  # num_size > digs_num
        (MIN_NUM_SIZE - 1, 5, "12345", "1-5"),
        (3, 6, "12345", "1-6"),  # digs_num != len(digs_set)
    ),
)
def test_difficulty_not_valid(num_size, digs_num, digs, digs_label):
    with pytest.raises(ValueError):
        Difficulty(num_size, digs_num, frozenset(digs), digs_label)


def test_difficulty_eq():
    assert (
        Difficulty(3, 6, frozenset("123456"), "1-6", "a")
        == Difficulty(3, 6, frozenset("abcdef"), "a-f", "b")
    )


def test_difficulty_ordering():
    difficulties = [
        Difficulty.new_default(5, 10, "abcd"),
        Difficulty.new_default(6, 10),
        Difficulty.new_default(3, 5),
    ]
    assert sorted(difficulties) == [
        Difficulty.new_default(3, 5),
        Difficulty.new_default(5, 10, "abcd"),
        Difficulty.new_default(6, 10),
    ]


def test_difficulty_frozen():
    difficulty = Difficulty.new_default(3, 6)
    with pytest.raises(FrozenInstanceError):
        difficulty.num_size = 10


# =====
# Round
# =====

# _bullscows
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
def test_bullscows(guess, number, bulls, cows):
    assert _bullscows(guess, number) == (bulls, cows)


# is_number_valid
# ---------------


@pytest.mark.parametrize(
    ("number", "difficulty"),
    (
        ("163", Difficulty.new_default(3, 6)),
        ("1593", Difficulty.new_default(4, 9)),
        ("2f5a9", Difficulty.new_default(5, 15)),
    )
)
def test_is_number_valid(number, difficulty):
    assert is_number_valid(number, difficulty)


@pytest.mark.parametrize(
    ("number", "difficulty"),
    (
        ("301", Difficulty.new_default(3, 6)),
        ("51a9", Difficulty.new_default(4, 9)),
        ("1g4a8", Difficulty.new_default(5, 15)),
    )
)
def test_is_number_valid_wrong_characters(number, difficulty):
    assert not is_number_valid(number, difficulty)


@pytest.mark.parametrize(
    ("number", "difficulty"),
    (
        ("1234", Difficulty.new_default(3, 5)),
        ("34", Difficulty.new_default(3, 5)),
        ("12349", Difficulty.new_default(4, 9)),
        ("31", Difficulty.new_default(4, 9)),
        ("12f3a49b", Difficulty.new_default(5, 15)),
        ("31d", Difficulty.new_default(5, 15)),
    )
)
def test_is_number_valid_wrong_length(number, difficulty):
    assert not is_number_valid(number, difficulty)


@pytest.mark.parametrize(
    ("number", "difficulty"),
    (
        ("232", Difficulty.new_default(3, 5)),
        ("3727", Difficulty.new_default(4, 9)),
        ("3b5b8", Difficulty.new_default(5, 15)),
    )
)
def test_is_number_valid_not_unique_characters(number, difficulty):
    assert not is_number_valid(number, difficulty)


# draw_number
# -----------


@pytest.mark.parametrize(
    "difficulty",
    (
        Difficulty.new_default(3, 6),
        Difficulty.new_default(4, 9),
        Difficulty.new_default(5, 15),
    )
)
def test_draw_number(difficulty):
    number = draw_number(difficulty)
    assert is_number_valid(number, difficulty)


# RoundCore
# ---------


def test_round_core():
    number = "123"
    difficulty = Difficulty.new_default(3, 6)
    round_core = RoundCore(number, difficulty)

    # After initiation
    assert round_core.difficulty == difficulty
    assert not round_core.history
    assert not round_core.steps
    assert not round_core.closed
    with pytest.raises(AttributeError):
        round_core.score_data

    # first step
    guess1 = "145"
    bullscows1 = _bullscows(guess1, number)
    assert round_core.send(guess1) == bullscows1
    assert round_core.history == [(guess1, *bullscows1)]
    assert round_core.steps == 1

    # second step

    guess2 = "152"
    bullscows2 = _bullscows(guess2, number)
    assert round_core.send(guess2) == bullscows2
    assert round_core.history == [(guess1, *bullscows1), (guess2, *bullscows2)]
    assert round_core.steps == 2

    # succesive guess
    with pytest.raises(StopIteration):
        round_core.send(number)
    assert round_core.history == [
        (guess1, *bullscows1),
        (guess2, *bullscows2),
        (number, difficulty.num_size, 0)
    ]
    assert round_core.steps == 3
    assert round_core.closed

    # closed
    with pytest.raises(StopIteration):
        round_core.send(number)
    score_data = round_core.score_data
    assert score_data.dt
    assert score_data.difficulty == difficulty.to_simple()
    assert score_data.score == 3
