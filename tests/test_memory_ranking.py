from datetime import datetime

import pytest

from bacpy.core import (
    Difficulty,
    Ranking,
    RankingRecord,
)
from bacpy.memory_ranking import MemoryRankingRepo
from tests.ranking import BaseTest_RankingRepo


@pytest.fixture
def ranking_repo():
    return MemoryRankingRepo()


class Test_MemoryRankingRepo(BaseTest_RankingRepo):

    def test_initiating_data(self):
        difficulty1 = Difficulty(5, 8)
        data1 = [
                RankingRecord(8, datetime(2021, 2, 18), "Maciek"),
                RankingRecord(15, datetime(2021, 6, 4), "Tomasz"),
        ]
        difficulty2 = Difficulty(4, 9)
        data2 = [
                RankingRecord(17, datetime(2021, 4, 5), "Piotrek"),
        ]
        ranking_repo = MemoryRankingRepo({difficulty1: data1, difficulty2: data2})
        assert ranking_repo.load(difficulty1) == Ranking(tuple(data1), difficulty1)
        assert ranking_repo.load(difficulty2) == Ranking(tuple(data2), difficulty2)
