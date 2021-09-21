import pytest

from bacpy.utils import SequenceView


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
