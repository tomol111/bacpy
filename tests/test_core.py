import pytest

from bacpy.core import (
    Difficulty,
    Digits,
    draw_number,
    GuessHandler,
    is_number_valid,
    is_player_name_valid,
    MIN_NUM_SIZE,
    NumberParams,
    standard_digits,
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
