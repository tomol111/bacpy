from datetime import datetime

import pytest

from bacpy.core import (
    Difficulty,
    Digits,
    draw_number,
    FileRankingManager,
    GuessHandler,
    is_number_valid,
    is_player_name_valid,
    MIN_NUM_SIZE,
    NumberParams,
    Ranking,
    _RankingRecord,
    _ScoreData,
    standard_digits,
)


# =============
# Ranking tools
# =============


# FileRankingManager
# --------------


# TODO: test backward compatibility by snapshotting file


def test_FileRankingManager_load__not_existing_ranking(tmp_path):
    ranking_manager = FileRankingManager(tmp_path)
    difficulty = Difficulty(4, 6)
    assert ranking_manager.load(difficulty) == Ranking((), difficulty)


def test_FileRankingManager_is_score_fit_into__not_full(tmp_path):
    difficulty = Difficulty(3, 6)
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
    difficulty = Difficulty(3, 6)
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
    difficulty = Difficulty(5, 8)
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
    difficulty = Difficulty(3, 6)
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
    difficulty = Difficulty(3, 6)
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
    difficulty1 = Difficulty(4, 8)
    difficulty2 = Difficulty(4, 10)
    difficulty3 = Difficulty(3, 5)
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


# ===============
# standard_digits
# ===============


@pytest.mark.parametrize(
    "digits_num, digits_sequence, description",
    (
        (2, "12", "[1-2]"),
        (6, "123456", "[1-6]"),
        (9, "123456789", "[1-9]"),
        (10, "123456789a", "[1-9a]"),
        (13, "123456789abcd", "[1-9a-d]"),
        (35, "123456789abcdefghijklmnopqrstuvwxyz", "[1-9a-z]"),
    ),
)
def test_standard_digits(digits_num, digits_sequence, description):
    digits = standard_digits(digits_num)
    assert digits.data == frozenset(digits_sequence)
    assert digits.description == description


@pytest.mark.parametrize(
    "digits_num",
    (-2, 0, 1, 36, 50),
)
def test_standard_digits__raise_ValueError_on_invalid_digits_num(digits_num):
    with pytest.raises(ValueError):
        standard_digits(digits_num)


# ============
# Difficulties
# ============


def test_Difficulty_init():
    number_size = 3
    digits_num = 6
    difficulty = Difficulty(number_size, digits_num)
    assert difficulty.number_size == number_size
    assert difficulty.digits_num == digits_num


@pytest.mark.parametrize(
    ("number_size", "digits_num"),
    (
        (6, 6),  # number_size == digits_num
        (7, 5),  # number_size > digits_num
        (MIN_NUM_SIZE - 1, 5),
    ),
)
def test_Difficulty__not_valid_arguments(number_size, digits_num):
    with pytest.raises(ValueError):
        Difficulty(number_size, digits_num)


# ============
# NumberParams
# ============


def test_NumberParams_init():
    number_params = NumberParams(
        Difficulty(5, 7), frozenset("1234567"), "[1-7]", "number parameters"
    )
    assert number_params.difficulty == Difficulty(5, 7)
    assert number_params.number_size == 5
    assert number_params.digits_num == 7
    assert number_params.digits_set == frozenset("1234567")
    assert number_params.digits_description == "[1-7]"
    assert number_params.label == "number parameters"


def test_NumberParams_from_digits_factory():
    def digits_factory(digits_num):
        assert digits_num == 4
        return Digits(frozenset("1234"), "[1-4]")

    number_params = NumberParams.from_digits_factory(
        Difficulty(3, 4), digits_factory, "label"
    )

    assert number_params.difficulty == Difficulty(3, 4)
    assert number_params.number_size == 3
    assert number_params.digits_num == 4
    assert number_params.digits_set == frozenset("1234")
    assert number_params.digits_description == "[1-4]"
    assert number_params.label == "label"


def test_NumberParams_standard():
    number_params = NumberParams.standard(Difficulty(3, 6), "some label")
    assert number_params.number_size == 3
    assert number_params.digits_num == 6
    assert number_params.digits_set == frozenset("123456")
    assert number_params.digits_description == "[1-6]"
    assert number_params.label == "some label"


@pytest.mark.parametrize(
    "difficulty, digits, digits_description",
    (
        (Difficulty(3, 6), "12345", "[1-6]"),  # digits_num > len(digits_set)
        (Difficulty(4, 5), "1234567", "[1-6]"),  # digits_num < len(digits_set)
    ),
)
def test_NumberParams__invalid_arguments(difficulty, digits, digits_description):
    with pytest.raises(ValueError):
        NumberParams(difficulty, frozenset(digits), digits_description)


# =====
# Round
# =====


# is_number_valid
# ---------------


@pytest.mark.parametrize(
    "number, number_params",
    (
        ("163", NumberParams.standard(Difficulty(3, 6))),
        ("1593", NumberParams.standard(Difficulty(4, 9))),
        ("2f5a9", NumberParams.standard(Difficulty(5, 15))),
    )
)
def test_is_number_valid(number, number_params):
    assert is_number_valid(number, number_params)


@pytest.mark.parametrize(
    "number, number_params",
    (
        ("301", NumberParams.standard(Difficulty(3, 6))),
        ("51a9", NumberParams.standard(Difficulty(4, 9))),
        ("1g4a8", NumberParams.standard(Difficulty(5, 15))),
    )
)
def test_is_number_valid__wrong_characters(number, number_params):
    assert not is_number_valid(number, number_params)


@pytest.mark.parametrize(
    "number, number_params",
    (
        ("1234", NumberParams.standard(Difficulty(3, 5))),
        ("34", NumberParams.standard(Difficulty(3, 5))),
        ("12349", NumberParams.standard(Difficulty(4, 9))),
        ("31", NumberParams.standard(Difficulty(4, 9))),
        ("12f3a49b", NumberParams.standard(Difficulty(5, 15))),
        ("31d", NumberParams.standard(Difficulty(5, 15))),
    )
)
def test_is_number_valid__wrong_length(number, number_params):
    assert not is_number_valid(number, number_params)


@pytest.mark.parametrize(
    "number, number_params",
    (
        ("232", NumberParams.standard(Difficulty(3, 5))),
        ("3727", NumberParams.standard(Difficulty(4, 9))),
        ("3b5b8", NumberParams.standard(Difficulty(5, 15))),
    )
)
def test_is_number_valid__not_unique_characters(number, number_params):
    assert not is_number_valid(number, number_params)


# draw_number
# -----------


@pytest.mark.parametrize(
    "number_params",
    (
        NumberParams.standard(Difficulty(3, 6)),
        NumberParams.standard(Difficulty(4, 9)),
        NumberParams.standard(Difficulty(5, 15)),
    )
)
def test_draw_number(number_params):
    number = draw_number(number_params)
    assert is_number_valid(number, number_params)


# RoundCore
# ---------


def test_GuessHandler():
    number = "1234"
    number_params = NumberParams.standard(Difficulty(4, 8))
    guess_handler = GuessHandler(number, number_params)

    # After initiation
    assert guess_handler.number_params == number_params
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
    assert score_data.difficulty == number_params.difficulty
    assert score_data.score == 4
