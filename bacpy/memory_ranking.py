from typing import Dict, Iterator, List, Optional

from bacpy.core import (
    Difficulty,
    is_player_name_valid,
    Ranking,
    RankingManager,
    RankingRecord,
    RANKING_SIZE,
    ScoreData,
)


class MemoryRankingManager(RankingManager):

    def __init__(
            self,
            init_data: Optional[Dict[Difficulty, List[RankingRecord]]] = None,
    ) -> None:
        self._data = init_data or {}

    def load(self, difficulty: Difficulty) -> Ranking:
        return Ranking(
            data=tuple(self._data.get(difficulty, ())),
            difficulty=difficulty,
        )

    def update(self, score_data: ScoreData, player: str) -> Ranking:
        assert is_player_name_valid(player)
        self._data.setdefault(score_data.difficulty, []).append(
            RankingRecord(
                score_data.score,
                score_data.dt,
                player,
            )
        )
        self._data[score_data.difficulty].sort()
        del self._data[score_data.difficulty][RANKING_SIZE:]
        return self.load(score_data.difficulty)

    def available_difficulties(self) -> Iterator[Difficulty]:
        yield from self._data
