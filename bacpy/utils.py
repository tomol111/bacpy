from __future__ import annotations

from typing import overload, Sequence, TypeVar


# Type variables
T_co = TypeVar("T_co", covariant=True)


# ============
# SequenceView
# ============


class SequenceView(Sequence[T_co]):

    def __init__(self, data: Sequence[T_co]) -> None:
        self._data = data

    @overload
    def __getitem__(self, index: int) -> T_co: ...

    @overload
    def __getitem__(self, index: slice) -> Sequence[T_co]: ...

    def __getitem__(self, index):
        return self._data[index]

    def __len__(self) -> int:
        return len(self._data)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, SequenceView):
            return self._data == other._data
        return self._data == other

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._data!r})"
