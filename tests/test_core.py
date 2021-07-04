from dataclasses import FrozenInstanceError
from datetime import datetime
from pathlib import Path

import pytest

from bacpy.core import (
    _comput_bullscows,
    default_digs_range,
    default_digs_set,
    Difficulty,
    DIGITS_RANGE,
    draw_number,
    GameException,
    GuessingRecord,
    is_number_valid,
    MIN_NUM_SIZE,
    QuitGame,
    Ranking,
    RankingManager,
    _RankingRecord,
    RANKING_SIZE,
    RestartGame,
    RoundCore,
    _ScoreData,
    SequenceView,
    SimpleDifficulty,
    StopPlaying,
    _validate_digs_num_for_defaults,
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
    difficulty = Difficulty.new_default(3, 5)
    exception = RestartGame(difficulty)
    assert exception.difficulty == difficulty


# =============
# Ranking tools
# =============


# _RankingRecord
# --------------


def test_ranking_record_as_tuple():
    score_data = _RankingRecord(
        10,
        datetime(2021, 6, 5),
        "player name",
    )
    assert isinstance(score_data, tuple)


def test_ranking_record_as_namespace():
    dt = datetime(2021, 6, 5)
    score = 10
    player = "player name"
    score_data = _RankingRecord(
        dt=dt,
        score=score,
        player=player,
    )
    assert score_data.score == score
    assert score_data.dt == dt
    assert score_data.player == player


# Ranking
# -------


def test_ranking_init():
    data = [
        _RankingRecord(10, datetime(2021, 6, 5), "Tomek"),
        _RankingRecord(15, datetime(2021, 6, 4), "Tomasz"),
    ]
    difficulty = SimpleDifficulty(3, 6)
    ranking = Ranking(data, difficulty)
    assert ranking.data == data
    assert ranking.difficulty == difficulty


def test_ranking_init_sorting():
    data = [
        _RankingRecord(10, datetime(2021, 6, 5), "Tomek"),
        _RankingRecord(15, datetime(2021, 6, 4), "Tomasz"),
        _RankingRecord(12, datetime(2021, 6, 6), "New player"),
    ]
    sorted_data = [
        _RankingRecord(10, datetime(2021, 6, 5), "Tomek"),
        _RankingRecord(12, datetime(2021, 6, 6), "New player"),
        _RankingRecord(15, datetime(2021, 6, 4), "Tomasz"),
    ]
    ranking = Ranking(data, SimpleDifficulty(3, 6))
    assert ranking.data == sorted_data


def test_ranking_eq():
    data = [
        _RankingRecord(10, datetime(2021, 6, 5), "Tomek"),
        _RankingRecord(15, datetime(2021, 6, 4), "Tomasz"),
    ]
    difficulty = SimpleDifficulty(3, 6)
    ranking0 = Ranking(data, difficulty)
    ranking1 = Ranking(data, difficulty)
    assert ranking0 == ranking1


def test_ranking_ne_difrent_difficulties():
    data = [
        _RankingRecord(10, datetime(2021, 6, 5), "Tomek"),
        _RankingRecord(15, datetime(2021, 6, 4), "Tomasz"),
    ]
    ranking0 = Ranking(data, SimpleDifficulty(3, 6))
    ranking1 = Ranking(data, SimpleDifficulty(4, 9))
    assert not ranking0 == ranking1


def test_ranking_ne_difrent_data():
    data0 = [
        _RankingRecord(10, datetime(2021, 6, 5), "Tomek"),
        _RankingRecord(15, datetime(2021, 6, 4), "Tomasz"),
    ]
    data1 = data0 + [
        _RankingRecord(12, datetime(2021, 6, 6), "New player")
    ]
    difficulty = SimpleDifficulty(3, 6)
    ranking0 = Ranking(data0, difficulty)
    ranking1 = Ranking(data1, difficulty)
    assert not ranking0 == ranking1


def test_ranking_add():
    data = [
        _RankingRecord(10, datetime(2021, 6, 5), "Tomek"),
        _RankingRecord(15, datetime(2021, 6, 4), "Tomasz"),
    ]
    expected_data = [
        _RankingRecord(10, datetime(2021, 6, 5), "Tomek"),
        _RankingRecord(12, datetime(2021, 6, 6), "New player"),
        _RankingRecord(15, datetime(2021, 6, 4), "Tomasz"),
    ]
    ranking = Ranking(data, SimpleDifficulty(3, 6))
    ranking.add(
        _RankingRecord(12, datetime(2021, 6, 6), "New player")
    )
    assert ranking.data == expected_data


def test_ranking_add_overflow():
    data = [
        _RankingRecord(6, datetime(2021, 3, 17), "Tomasz"),
        _RankingRecord(8, datetime(2021, 2, 18), "Maciek"),
        _RankingRecord(10, datetime(2021, 6, 5), "Tomek"),
        _RankingRecord(15, datetime(2021, 6, 4), "Tomasz"),
        _RankingRecord(15, datetime(2021, 6, 6), "Zofia"),
        _RankingRecord(17, datetime(2021, 4, 5), "Piotrek"),
        _RankingRecord(20, datetime(2020, 12, 30), "Tomasz"),
        _RankingRecord(21, datetime(2021, 3, 20), "Tomasz"),
        _RankingRecord(30, datetime(2020, 11, 10), "Darek"),
        _RankingRecord(32, datetime(2020, 8, 1), "Tomasz"),
    ]
    expected_data = [
        _RankingRecord(6, datetime(2021, 3, 17), "Tomasz"),
        _RankingRecord(8, datetime(2021, 2, 18), "Maciek"),
        _RankingRecord(10, datetime(2021, 6, 5), "Tomek"),
        _RankingRecord(12, datetime(2021, 6, 6), "New player"),
        _RankingRecord(15, datetime(2021, 6, 4), "Tomasz"),
        _RankingRecord(15, datetime(2021, 6, 6), "Zofia"),
        _RankingRecord(17, datetime(2021, 4, 5), "Piotrek"),
        _RankingRecord(20, datetime(2020, 12, 30), "Tomasz"),
        _RankingRecord(21, datetime(2021, 3, 20), "Tomasz"),
        _RankingRecord(30, datetime(2020, 11, 10), "Darek"),
    ]
    ranking = Ranking(data, SimpleDifficulty(3, 6))
    ranking.add(
        _RankingRecord(12, datetime(2021, 6, 6), "New player")
    )
    assert ranking.data == expected_data


# _ScoreData
# ----------


def test_score_data_as_tuple():
    score_data = _ScoreData(
        10,
        datetime(2021, 6, 5),
        SimpleDifficulty(3, 6),
    )
    assert isinstance(score_data, tuple)


def test_score_data_as_namespace():
    score = 10
    dt = datetime(2021, 6, 5)
    difficulty = SimpleDifficulty(3, 6)
    score_data = _ScoreData(
        score=score,
        dt=dt,
        difficulty=difficulty,
    )
    assert score_data.score == score
    assert score_data.dt == dt
    assert score_data.difficulty == difficulty


# RankingManager
# --------------


def test_ranking_manager_get_path():
    path = Path("some_dir")
    assert RankingManager(path)._get_path(
        SimpleDifficulty(3, 6)
    ) == path / "3_6.csv"


def test_ranking_manager_save_load_unitarity(tmp_path):
    ranking_manager = RankingManager(tmp_path)
    difficulty = SimpleDifficulty(3, 6)
    ranking = Ranking(
        [
            _RankingRecord(10, datetime(2021, 6, 5), "Tomek"),
            _RankingRecord(15, datetime(2021, 6, 4), "Tomasz"),
        ],
        difficulty,
    )
    ranking_manager._save(ranking)
    assert ranking_manager.load(difficulty) == ranking


def test_ranking_manager_load_not_existing_ranking(tmp_path):
    ranking_manager = RankingManager(tmp_path)
    difficulty = SimpleDifficulty(3, 6)
    expected_empty_ranking = Ranking([], difficulty)

    assert ranking_manager.load(difficulty) == expected_empty_ranking
    assert ranking_manager._get_path(difficulty).exists()


def test_ranking_manager_is_not_empty(tmp_path):
    difficulty = SimpleDifficulty(3, 6)
    ranking_manager = RankingManager(tmp_path)

    assert not ranking_manager.is_not_empty(difficulty)

    ranking_manager._get_path(difficulty).touch()
    assert not ranking_manager.is_not_empty(difficulty)

    ranking_manager._save(
        Ranking(
            [_RankingRecord(10, datetime(2021, 6, 5), "Tomek")],
            difficulty,
        ),
    )
    assert ranking_manager.is_not_empty(difficulty)


def test_ranking_manager_is_score_fit_into_not_full(tmp_path):
    difficulty = SimpleDifficulty(3, 6)
    ranking_manager = RankingManager(tmp_path)
    ranking = Ranking(
        [
            _RankingRecord(10, datetime(2021, 6, 5), "Tomek"),
            _RankingRecord(15, datetime(2021, 6, 4), "Tomasz"),
        ],
        difficulty,
    )
    ranking_manager._save(ranking)
    assert ranking_manager.is_score_fit_into(
        _ScoreData(12, datetime(2021, 6, 6), difficulty)
    )
    assert ranking_manager.is_score_fit_into(
        _ScoreData(16, datetime(2021, 6, 7), difficulty)
    )


def test_ranking_manager_is_score_fit_into_full(tmp_path):
    assert RANKING_SIZE == 10, "Ranking size changed"
    difficulty = SimpleDifficulty(3, 6)
    ranking_manager = RankingManager(tmp_path)
    ranking = Ranking(
        [
            _RankingRecord(6, datetime(2021, 3, 17), "Tomasz"),
            _RankingRecord(8, datetime(2021, 2, 18), "Maciek"),
            _RankingRecord(10, datetime(2021, 6, 5), "Tomek"),
            _RankingRecord(15, datetime(2021, 6, 4), "Tomasz"),
            _RankingRecord(15, datetime(2021, 6, 6), "Zofia"),
            _RankingRecord(17, datetime(2021, 4, 5), "Piotrek"),
            _RankingRecord(20, datetime(2020, 12, 30), "Tomasz"),
            _RankingRecord(21, datetime(2021, 3, 20), "Tomasz"),
            _RankingRecord(30, datetime(2020, 11, 10), "Darek"),
            _RankingRecord(32, datetime(2020, 8, 1), "Tomasz"),
        ],
        difficulty,
    )
    ranking_manager._save(ranking)

    assert ranking_manager.is_score_fit_into(
        _ScoreData(12, datetime(2021, 6, 6), difficulty)
    )
    assert not ranking_manager.is_score_fit_into(
        _ScoreData(33, datetime(2021, 6, 6), difficulty)
    )


def test_ranking_manager_update_not_full(tmp_path):
    assert RANKING_SIZE == 10, "Ranking size changed"
    difficulty = SimpleDifficulty(3, 6)
    ranking_manager = RankingManager(tmp_path)
    ranking = Ranking(
        [
            (10, datetime(2021, 6, 5), "Tomek"),
            (15, datetime(2021, 6, 4), "Tomasz"),
        ],
        difficulty,
    )
    ranking_manager._save(ranking)
    expected_ranking = Ranking(
        [
            (10, datetime(2021, 6, 5), "Tomek"),
            (12, datetime(2021, 6, 6), "New player"),
            (15, datetime(2021, 6, 4), "Tomasz"),
        ],
        difficulty,
    )
    score_data = _ScoreData(12, datetime(2021, 6, 6), difficulty)

    updated_ranking = ranking_manager.update(score_data, "New player")

    assert updated_ranking == expected_ranking


def test_ranking_mamager_update_full(tmp_path):
    difficulty = SimpleDifficulty(3, 6)
    ranking_manager = RankingManager(tmp_path)
    ranking = Ranking(
        [
            _RankingRecord(6, datetime(2021, 3, 17), "Tomasz"),
            _RankingRecord(8, datetime(2021, 2, 18), "Maciek"),
            _RankingRecord(10, datetime(2021, 6, 5), "Tomek"),
            _RankingRecord(15, datetime(2021, 6, 4), "Tomasz"),
            _RankingRecord(15, datetime(2021, 6, 6), "Zofia"),
            _RankingRecord(17, datetime(2021, 4, 5), "Piotrek"),
            _RankingRecord(20, datetime(2020, 12, 30), "Tomasz"),
            _RankingRecord(21, datetime(2021, 3, 20), "Tomasz"),
            _RankingRecord(30, datetime(2020, 11, 10), "Darek"),
            _RankingRecord(32, datetime(2020, 8, 1), "Tomasz"),
        ],
        difficulty,
    )
    ranking_manager._save(ranking)
    expected_ranking = Ranking(
        [
            _RankingRecord(6, datetime(2021, 3, 17), "Tomasz"),
            _RankingRecord(8, datetime(2021, 2, 18), "Maciek"),
            _RankingRecord(10, datetime(2021, 6, 5), "Tomek"),
            _RankingRecord(12, datetime(2021, 6, 6), "New player"),
            _RankingRecord(15, datetime(2021, 6, 4), "Tomasz"),
            _RankingRecord(15, datetime(2021, 6, 6), "Zofia"),
            _RankingRecord(17, datetime(2021, 4, 5), "Piotrek"),
            _RankingRecord(20, datetime(2020, 12, 30), "Tomasz"),
            _RankingRecord(21, datetime(2021, 3, 20), "Tomasz"),
            _RankingRecord(30, datetime(2020, 11, 10), "Darek"),
        ],
        difficulty,
    )
    score_data = _ScoreData(12, datetime(2021, 6, 6), difficulty)

    updated_ranking = ranking_manager.update(score_data, "New player")

    assert updated_ranking == expected_ranking
    assert updated_ranking == ranking_manager.load(difficulty)


def test_ranking_manager_update_overflow(tmp_path):
    difficulty = SimpleDifficulty(3, 6)
    ranking_manager = RankingManager(tmp_path)
    ranking = Ranking(
        [
            _RankingRecord(6, datetime(2021, 3, 17), "Tomasz"),
            _RankingRecord(8, datetime(2021, 2, 18), "Maciek"),
            _RankingRecord(10, datetime(2021, 6, 5), "Tomek"),
            _RankingRecord(15, datetime(2021, 6, 4), "Tomasz"),
            _RankingRecord(15, datetime(2021, 6, 6), "Zofia"),
            _RankingRecord(17, datetime(2021, 4, 5), "Piotrek"),
            _RankingRecord(20, datetime(2020, 12, 30), "Tomasz"),
            _RankingRecord(21, datetime(2021, 3, 20), "Tomasz"),
            _RankingRecord(30, datetime(2020, 11, 10), "Darek"),
            _RankingRecord(32, datetime(2020, 8, 1), "Tomasz"),
        ],
        difficulty,
    )
    ranking_manager._save(ranking)
    score_data = _ScoreData(35, datetime(2021, 6, 6), difficulty)

    updated_ranking = ranking_manager.update(score_data, "New player")

    assert updated_ranking == ranking
    assert updated_ranking == ranking_manager.load(difficulty)


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
def test_default_digs_range(digs_num, expected):
    assert default_digs_range(digs_num) == expected


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
        default_digs_range(digs_num)


def test_difficulty_inheritance():
    assert issubclass(Difficulty, SimpleDifficulty)


def test_difficulty_init():
    num_size = 3
    digs_num = 6
    digs_set = frozenset("123456")
    digs_range = "1-6"
    name = "name_str"
    difficulty = Difficulty(num_size, digs_num, digs_set, digs_range, name)
    assert difficulty.num_size == num_size
    assert difficulty.digs_num == digs_num
    assert difficulty.digs_set == digs_set
    assert difficulty.digs_range == digs_range
    assert difficulty.name == name


def test_difficulty_new_default():
    difficulty = Difficulty.new_default(3, 6, "some name")
    assert difficulty.num_size == 3
    assert difficulty.digs_num == 6
    assert difficulty.digs_set == frozenset("123456")
    assert difficulty.digs_range == "1-6"
    assert difficulty.name == "some name"


@pytest.mark.parametrize(
    ("num_size", "digs_num", "digs", "digs_range"),
    (
        (6, 6, "123456", "1-6"),  # num_size == digs_num
        (7, 5, "12345", "1-5"),  # num_size > digs_num
        (MIN_NUM_SIZE - 1, 5, "12345", "1-5"),
        (3, 6, "12345", "1-6"),  # digs_num != len(digs_set)
    ),
)
def test_difficulty_not_valid(num_size, digs_num, digs, digs_range):
    with pytest.raises(ValueError):
        Difficulty(num_size, digs_num, frozenset(digs), digs_range)


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


def test_sequence_view_eq():
    lst = [1, 2, 3, 2, 2]
    assert SequenceView(lst.copy()) == SequenceView(lst.copy())


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
        (Difficulty.new_default(3, 6), "163"),
        (Difficulty.new_default(4, 9), "1593"),
        (Difficulty.new_default(5, 15), "2f5a9"),
    )
)
def test_is_number_valid(difficulty, number):
    assert is_number_valid(difficulty, number)


@pytest.mark.parametrize(
    ("difficulty", "number"),
    (
        (Difficulty.new_default(3, 6), "301"),
        (Difficulty.new_default(4, 9), "51a9"),
        (Difficulty.new_default(5, 15), "1g4a8"),
    )
)
def test_is_number_valid_wrong_characters(difficulty, number):
    assert not is_number_valid(difficulty, number)


@pytest.mark.parametrize(
    ("difficulty", "number"),
    (
        (Difficulty.new_default(3, 5), "1234"),
        (Difficulty.new_default(3, 5), "34"),
        (Difficulty.new_default(4, 9), "12349"),
        (Difficulty.new_default(4, 9), "31"),
        (Difficulty.new_default(5, 15), "12f3a49b"),
        (Difficulty.new_default(5, 15), "31d"),
    )
)
def test_is_number_valid_wrong_length(difficulty, number):
    assert not is_number_valid(difficulty, number)


@pytest.mark.parametrize(
    ("difficulty", "number"),
    (
        (Difficulty.new_default(3, 5), "232"),
        (Difficulty.new_default(4, 9), "3727"),
        (Difficulty.new_default(5, 15), "3b5b8"),
    )
)
def test_is_number_valid_not_unique_characters(difficulty, number):
    assert not is_number_valid(difficulty, number)


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
    assert is_number_valid(difficulty, number)


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
    assert not round_core.finished
    with pytest.raises(AttributeError):
        round_core.score_data

    # invalid number
    with pytest.raises(ValueError):
        round_core.parse_guess("")
    assert not round_core.history
    assert not round_core.steps

    # first step
    guess_record_0 = round_core.parse_guess("145")
    assert guess_record_0.number == "145"
    assert guess_record_0.bulls == 1
    assert guess_record_0.cows == 0
    assert round_core.history == [guess_record_0]
    assert round_core.steps == 1

    # second step
    guess_record_1 = round_core.parse_guess("152")
    assert guess_record_1.number == "152"
    assert guess_record_1.bulls == 1
    assert guess_record_1.cows == 1
    assert round_core.history == [guess_record_0, guess_record_1]
    assert round_core.steps == 2

    # succesive guess
    guess_record_last = round_core.parse_guess(number)
    assert guess_record_last.number == number
    assert guess_record_last.bulls == difficulty.num_size
    assert guess_record_last.cows == 0
    assert round_core.history == [
        guess_record_0, guess_record_1, guess_record_last
    ]
    assert round_core.steps == 3
    assert round_core.finished

    # finished
    with pytest.raises(RuntimeError):
        round_core.parse_guess(number)
    score_data = round_core.score_data
    assert score_data.dt
    assert score_data.difficulty == difficulty.to_simple()
    assert score_data.score == 3
