from datetime import datetime

import pytest

from bacpy.core import (
    standard_digs_label,
    standard_digs_set,
    Difficulty,
    DIGITS_SEQUENCE,
    draw_number,
    FileRankingManager,
    is_number_valid,
    is_player_name_valid,
    MIN_NUM_SIZE,
    Ranking,
    _RankingRecord,
    GuessHandler,
    _ScoreData,
    SimpleDifficulty,
    _validate_digs_num_for_standard_difficulty,
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


def test_FileRankingManager_update__not_full(tmp_path):
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


def test_FileRankingManager_update__overflow(tmp_path):
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


def test_FileRankingManager_available_difficulties(tmp_path):
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
def test_validate_player_name__valid(name):
    assert is_player_name_valid(name)


@pytest.mark.parametrize(
    "name",
    ("", "ab", "abcdefghijklmnopqrstu", "abcdefghijklmnopqrstuvwxyz")
)
def test_validate_player_name__invalid(name):
    assert not is_player_name_valid(name)


# ============
# Difficulties
# ============


def test_SimpleDifficulty_init():
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
def test_SimpleDifficulty__not_valid_arguments(num_size, digs_num):
    with pytest.raises(ValueError):
        SimpleDifficulty(num_size, digs_num)


def test_SimpleDifficulty_eq():
    assert (
        SimpleDifficulty(3, 6)
        == SimpleDifficulty(3, 6)
    )


def test_SimpleDifficulty_ne():
    assert (
        SimpleDifficulty(3, 6)
        != SimpleDifficulty(3, 7)
    )


def test_SimpleDifficulty_ordering():
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


@pytest.mark.parametrize(
    "digs_num",
    (
        MIN_NUM_SIZE,
        MIN_NUM_SIZE + 3,
        len(DIGITS_SEQUENCE),
        len(DIGITS_SEQUENCE) - 3,
    ),
)
def test_validate_digs_num_for_standard_difficulty__valid(digs_num):
    _validate_digs_num_for_standard_difficulty(digs_num)


@pytest.mark.parametrize(
    "digs_num",
    (
        MIN_NUM_SIZE - 1,
        MIN_NUM_SIZE - 2,
        len(DIGITS_SEQUENCE) + 1,
        len(DIGITS_SEQUENCE) + 3,
    ),
)
def test_validate_digs_num_for_standard_difficulty__invalid(digs_num):
    with pytest.raises(ValueError):
        _validate_digs_num_for_standard_difficulty(digs_num)


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
def test_standard_digs_set(digs_num, digits):
    assert standard_digs_set(digs_num) == frozenset(digits)


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
def test_standard_digs_label(digs_num, expected):
    assert standard_digs_label(digs_num) == expected


@pytest.mark.parametrize(
    "digs_num",
    (
        MIN_NUM_SIZE - 1,
        len(DIGITS_SEQUENCE) + 1,
    ),
)
def test_standard_validation(digs_num):
    with pytest.raises(ValueError):
        standard_digs_set(digs_num)
    with pytest.raises(ValueError):
        standard_digs_label(digs_num)


def test_Difficulty_init():
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


def test_Difficulty_standard():
    difficulty = Difficulty.standard(3, 6, "some name")
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
def test_Difficulty__invalid_arguments(num_size, digs_num, digs, digs_label):
    with pytest.raises(ValueError):
        Difficulty(num_size, digs_num, frozenset(digs), digs_label)


def test_Difficulty_eq():
    assert (
        Difficulty(3, 6, frozenset("123456"), "1-6", "a")
        == Difficulty(3, 6, frozenset("abcdef"), "a-f", "b")
    )


def test_Difficulty_ordering():
    difficulties = [
        Difficulty.standard(5, 10, "abcd"),
        Difficulty.standard(6, 10),
        Difficulty.standard(3, 5),
    ]
    assert sorted(difficulties) == [
        Difficulty.standard(3, 5),
        Difficulty.standard(5, 10, "abcd"),
        Difficulty.standard(6, 10),
    ]


# =====
# Round
# =====


# is_number_valid
# ---------------


@pytest.mark.parametrize(
    ("number", "difficulty"),
    (
        ("163", Difficulty.standard(3, 6)),
        ("1593", Difficulty.standard(4, 9)),
        ("2f5a9", Difficulty.standard(5, 15)),
    )
)
def test_is_number_valid(number, difficulty):
    assert is_number_valid(number, difficulty)


@pytest.mark.parametrize(
    ("number", "difficulty"),
    (
        ("301", Difficulty.standard(3, 6)),
        ("51a9", Difficulty.standard(4, 9)),
        ("1g4a8", Difficulty.standard(5, 15)),
    )
)
def test_is_number_valid__wrong_characters(number, difficulty):
    assert not is_number_valid(number, difficulty)


@pytest.mark.parametrize(
    ("number", "difficulty"),
    (
        ("1234", Difficulty.standard(3, 5)),
        ("34", Difficulty.standard(3, 5)),
        ("12349", Difficulty.standard(4, 9)),
        ("31", Difficulty.standard(4, 9)),
        ("12f3a49b", Difficulty.standard(5, 15)),
        ("31d", Difficulty.standard(5, 15)),
    )
)
def test_is_number_valid__wrong_length(number, difficulty):
    assert not is_number_valid(number, difficulty)


@pytest.mark.parametrize(
    ("number", "difficulty"),
    (
        ("232", Difficulty.standard(3, 5)),
        ("3727", Difficulty.standard(4, 9)),
        ("3b5b8", Difficulty.standard(5, 15)),
    )
)
def test_is_number_valid__not_unique_characters(number, difficulty):
    assert not is_number_valid(number, difficulty)


# draw_number
# -----------


@pytest.mark.parametrize(
    "difficulty",
    (
        Difficulty.standard(3, 6),
        Difficulty.standard(4, 9),
        Difficulty.standard(5, 15),
    )
)
def test_draw_number(difficulty):
    number = draw_number(difficulty)
    assert is_number_valid(number, difficulty)


# RoundCore
# ---------


def test_GuessHandler():
    number = "1234"
    difficulty = Difficulty.standard(4, 8)
    guess_handler = GuessHandler(number, difficulty)

    # After initiation
    assert guess_handler.difficulty == difficulty
    assert not guess_handler.history
    assert not guess_handler.steps_done
    assert not guess_handler.closed
    with pytest.raises(AttributeError):
        guess_handler.score_data

    # first step
    guess1 = "5678"
    bulls1, cows1 = 0, 0
    assert guess_handler.send(guess1) == (bulls1, cows1)
    assert guess_handler.history == [(guess1, bulls1, cows1)]
    assert guess_handler.steps_done == 1

    # second step
    guess2 = "3214"
    bulls2, cows2 = 2, 2
    assert guess_handler.send(guess2) == (bulls2, cows2)
    assert guess_handler.history == [(guess1, bulls1, cows1), (guess2, bulls2, cows2)]
    assert guess_handler.steps_done == 2

    # third step
    guess3 = "4321"
    bulls3, cows3 = 0, 4
    assert guess_handler.send(guess3) == (bulls3, cows3)
    assert guess_handler.history[-1] == (guess3, bulls3, cows3)
    assert guess_handler.steps_done == 3

    # succesive guess
    with pytest.raises(StopIteration):
        guess_handler.send(number)
    assert guess_handler.history[-1] == (number, 4, 0)
    assert guess_handler.steps_done == 4
    assert guess_handler.closed

    # closed
    with pytest.raises(StopIteration):
        guess_handler.send(number)
    score_data = guess_handler.score_data
    assert score_data.dt
    assert score_data.difficulty == difficulty.to_simple()
    assert score_data.score == 4
