from contextlib import suppress
from datetime import datetime
import pytest
from unittest import mock

from bacpy.core import (
    Difficulty,
    Digits,
    draw_number,
    GuessRecord,
    is_number_valid,
    is_player_name_valid,
    MIN_NUM_SIZE,
    NumberParams,
    Round,
    ScoreData,
    score_saver_factory,
    standard_digits,
)
from bacpy.memory_ranking import MemoryRankingRepo


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


# score_saver_factory
# -------------------

def test_score_saver_factory():
    score_data = ScoreData(3, datetime(2020, 4, 12), Difficulty(4, 7))
    ranking_repo = MemoryRankingRepo()
    parse_ranking = mock.Mock()

    score_saver = score_saver_factory(score_data, ranking_repo)
    score_saver("player", parse_ranking)

    ranking, = parse_ranking.call_args.args
    assert ranking.data[0] == (3, datetime(2020, 4, 12), "player")
    assert ranking_repo.load(Difficulty(4, 7)) == ranking


# Round
# -----


@mock.patch("bacpy.core.score_saver_factory", autospec=True)
@mock.patch("bacpy.core.draw_number", autospec=True)
def test_Round(mock_draw_number, mock_score_saver_factory):
    mock_draw_number.return_value = "1234"
    number_params = NumberParams.standard(Difficulty(4, 8))
    parse_guess_record = mock.Mock()
    parse_score = mock.Mock()
    ranking_repo = MemoryRankingRepo()
    round = Round(number_params, parse_guess_record, parse_score, ranking_repo)

    # After initiation
    assert round.number_params == number_params
    assert not round.history
    assert not round.steps_done
    assert not round.closed
    assert mock_draw_number.call_args == mock.call(number_params)

    # first step
    round.send("5678")
    assert round.steps_done == 1

    # second step
    round.send("3214")
    assert round.steps_done == 2

    # third step
    round.send("4321")
    assert round.steps_done == 3

    # succesive guess
    with pytest.raises(StopIteration):
        round.send("1234")
    assert round.steps_done == 4
    assert round.closed
    assert round.history == [
        ("5678", 0, 0),
        ("3214", 2, 2),
        ("4321", 0, 4),
        ("1234", 4, 0),
    ]

    # side effects
    assert parse_guess_record.call_args_list == [
        mock.call(GuessRecord("5678", 0, 0)),
        mock.call(GuessRecord("3214", 2, 2)),
        mock.call(GuessRecord("4321", 0, 4)),
        mock.call(GuessRecord("1234", 4, 0)),
    ]
    score, _ = parse_score.call_args.args
    assert score == 4

    # closed
    with pytest.raises(StopIteration):
        round.send("1234")


@mock.patch("bacpy.core.score_saver_factory", autospec=True)
@mock.patch("bacpy.core.draw_number", autospec=True)
def test_Round__parse_saver_with_score(mock_draw_number, mock_score_saver_factory):
    mock_draw_number.return_value = "135"
    mock_save_score = object()
    mock_score_saver_factory.return_value = mock_save_score
    number_params = NumberParams.standard(Difficulty(3, 6))
    parse_hints = mock.Mock()
    parse_score = mock.Mock()
    ranking_repo = MemoryRankingRepo()
    round = Round(number_params, parse_hints, parse_score, ranking_repo)

    round.send("123")
    round.send("456")
    with suppress(StopIteration):
        round.send("135")

    _, save_score = parse_score.call_args.args
    assert save_score is mock_save_score


@mock.patch("bacpy.core.draw_number", autospec=True)
def test_Round__do_not_parse_saver_with_score_if_score_do_not_fit_into_ranking(
        mock_draw_number
):
    mock_draw_number.return_value = "135"
    number_params = NumberParams.standard(Difficulty(3, 6))
    parse_hints = mock.Mock()
    parse_score = mock.Mock()
    ranking_repo = MemoryRankingRepo()
    ranking_repo.is_score_fit_into = (lambda score_data: False)
    round = Round(number_params, parse_hints, parse_score, ranking_repo)

    with suppress(StopIteration):
        round.send("135")

    _, save_score = parse_score.call_args.args
    assert not save_score
