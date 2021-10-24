import csv
from datetime import datetime
from pathlib import Path
from typing import Final, Iterator

from bacpy.core import (
    Difficulty,
    Ranking,
    RankingRepo,
    RankingRecord,
    ScoreData,
)


RANKINGS_DIR: Final[Path] = Path(".rankings")


class FileRankingRepo(RankingRepo):

    def __init__(self, rankings_dir: Path) -> None:
        self._rankings_dir = rankings_dir

    def load(self, difficulty: Difficulty) -> Ranking:
        path = self._get_path(difficulty)
        path.touch()
        with open(path, "r") as file:
            return Ranking(
                data=tuple(
                    RankingRecord(
                        int(score),
                        datetime.fromisoformat(dt),
                        player,
                    )
                    for score, dt, player in csv.reader(file)
                ),
                difficulty=difficulty,
            )

    def update(
            self,
            score_data: ScoreData,
            player: str,
    ) -> Ranking:
        updated_ranking = super().update(score_data, player)
        self._save(updated_ranking)
        return updated_ranking

    def _save(
            self,
            ranking: Ranking,
    ) -> None:
        path = self._get_path(ranking.difficulty)
        with open(path, "w") as file:
            writer = csv.writer(file)
            writer.writerows(ranking.data)

    def _get_path(self, difficulty: Difficulty) -> Path:
        return (
            self._rankings_dir
            / f"{difficulty.number_size}_{difficulty.digits_num}.csv"
        )

    def available_difficulties(self) -> Iterator[Difficulty]:
        for path in self._rankings_dir.iterdir():
            if path.stat().st_size:
                number_size, digits_num = map(int, path.stem.split("_"))
                yield Difficulty(number_size, digits_num)
