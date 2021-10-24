from datetime import datetime

from bacpy.core import (
    Difficulty,
    Ranking,
    RankingRecord,
    ScoreData,
)
from bacpy.memory_ranking import MemoryRankingRepo


def test_FileRankingRepo_load__not_existing_ranking():
    ranking_manager = MemoryRankingRepo()
    difficulty = Difficulty(4, 6)
    assert ranking_manager.load(difficulty) == Ranking((), difficulty)


def test_FileRankingRepo_is_score_fit_into__not_full():
    difficulty = Difficulty(3, 6)
    ranking_manager = MemoryRankingRepo()

    for score_data, player in (
            (ScoreData(10, datetime(2021, 6, 5), difficulty), "Tomek"),
            (ScoreData(15, datetime(2021, 6, 4), difficulty), "Tomasz"),
    ):
        ranking_manager.update(score_data, player)

    assert ranking_manager.is_score_fit_into(
        ScoreData(12, datetime(2021, 6, 6), difficulty)
    )
    assert ranking_manager.is_score_fit_into(
        ScoreData(16, datetime(2021, 6, 7), difficulty)
    )


def test_FileRankingRepo_is_score_fit_into__full():
    difficulty = Difficulty(3, 6)
    ranking_manager = MemoryRankingRepo()

    for score_data, player in (
            (ScoreData(6, datetime(2021, 3, 17), difficulty), "Tomasz"),
            (ScoreData(8, datetime(2021, 2, 18), difficulty), "Maciek"),
            (ScoreData(10, datetime(2021, 6, 5), difficulty), "Tomek"),
            (ScoreData(15, datetime(2021, 6, 4), difficulty), "Tomasz"),
            (ScoreData(15, datetime(2021, 6, 6), difficulty), "Zofia"),
            (ScoreData(17, datetime(2021, 4, 5), difficulty), "Piotrek"),
            (ScoreData(20, datetime(2020, 12, 30), difficulty), "Tomasz"),
            (ScoreData(21, datetime(2021, 3, 20), difficulty), "Tomasz"),
            (ScoreData(30, datetime(2020, 11, 10), difficulty), "Darek"),
            (ScoreData(32, datetime(2020, 8, 1), difficulty), "Tomasz"),
    ):
        ranking_manager.update(score_data, player)

    assert ranking_manager.is_score_fit_into(
        ScoreData(12, datetime(2021, 6, 6), difficulty)
    )
    assert not ranking_manager.is_score_fit_into(
        ScoreData(33, datetime(2021, 6, 6), difficulty)
    )


def test_FileRankingRepo_update__not_full():
    difficulty = Difficulty(5, 8)
    ranking_manager = MemoryRankingRepo()

    for score_data, player in (
            (ScoreData(15, datetime(2021, 6, 4), difficulty), "Tomasz"),
            (ScoreData(10, datetime(2021, 6, 5), difficulty), "Tomek"),
            (ScoreData(12, datetime(2021, 6, 6), difficulty), "Maciek"),
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


def test_FileRankingMamager_update__full():
    difficulty = Difficulty(3, 6)
    ranking_manager = MemoryRankingRepo()

    for score_data, player in (
            (ScoreData(32, datetime(2020, 8, 1), difficulty), "TO_DROP"),
            (ScoreData(30, datetime(2020, 11, 10), difficulty), "Darek"),
            (ScoreData(20, datetime(2020, 12, 30), difficulty), "Tomasz"),
            (ScoreData(6, datetime(2021, 3, 17), difficulty), "Tomasz"),
            (ScoreData(8, datetime(2021, 2, 18), difficulty), "Maciek"),
            (ScoreData(10, datetime(2021, 6, 5), difficulty), "Tomek"),
            (ScoreData(15, datetime(2021, 6, 4), difficulty), "Tomasz"),
            (ScoreData(15, datetime(2021, 6, 6), difficulty), "Zofia"),
            (ScoreData(17, datetime(2021, 4, 5), difficulty), "Piotrek"),
            (ScoreData(21, datetime(2021, 3, 20), difficulty), "Tomasz"),
            (ScoreData(12, datetime(2021, 6, 6), difficulty), "NEWEST")
    ):
        updated_ranking = ranking_manager.update(score_data, player)

    expected_ranking = Ranking(
        (
            RankingRecord(6, datetime(2021, 3, 17), "Tomasz"),
            RankingRecord(8, datetime(2021, 2, 18), "Maciek"),
            RankingRecord(10, datetime(2021, 6, 5), "Tomek"),
            RankingRecord(12, datetime(2021, 6, 6), "NEWEST"),
            RankingRecord(15, datetime(2021, 6, 4), "Tomasz"),
            RankingRecord(15, datetime(2021, 6, 6), "Zofia"),
            RankingRecord(17, datetime(2021, 4, 5), "Piotrek"),
            RankingRecord(20, datetime(2020, 12, 30), "Tomasz"),
            RankingRecord(21, datetime(2021, 3, 20), "Tomasz"),
            RankingRecord(30, datetime(2020, 11, 10), "Darek"),
        ),
        difficulty,
    )

    assert updated_ranking == expected_ranking
    assert updated_ranking == ranking_manager.load(difficulty)


def test_FileRankingRepo_update__overflow():
    difficulty = Difficulty(3, 6)
    ranking_manager = MemoryRankingRepo()

    for score_data, player in (
            (ScoreData(32, datetime(2020, 8, 1), difficulty), "Tomek"),
            (ScoreData(30, datetime(2020, 11, 10), difficulty), "Darek"),
            (ScoreData(20, datetime(2020, 12, 30), difficulty), "Tomasz"),
            (ScoreData(6, datetime(2021, 3, 17), difficulty), "Tomasz"),
            (ScoreData(8, datetime(2021, 2, 18), difficulty), "Maciek"),
            (ScoreData(10, datetime(2021, 6, 5), difficulty), "Tomek"),
            (ScoreData(15, datetime(2021, 6, 4), difficulty), "Tomasz"),
            (ScoreData(15, datetime(2021, 6, 6), difficulty), "Zofia"),
            (ScoreData(17, datetime(2021, 4, 5), difficulty), "Piotrek"),
            (ScoreData(21, datetime(2021, 3, 20), difficulty), "Tomasz"),
            (ScoreData(35, datetime(2021, 6, 6), difficulty), "NEWEST")
    ):
        updated_ranking = ranking_manager.update(score_data, player)

    expected_ranking = Ranking(
        (
            RankingRecord(6, datetime(2021, 3, 17), "Tomasz"),
            RankingRecord(8, datetime(2021, 2, 18), "Maciek"),
            RankingRecord(10, datetime(2021, 6, 5), "Tomek"),
            RankingRecord(15, datetime(2021, 6, 4), "Tomasz"),
            RankingRecord(15, datetime(2021, 6, 6), "Zofia"),
            RankingRecord(17, datetime(2021, 4, 5), "Piotrek"),
            RankingRecord(20, datetime(2020, 12, 30), "Tomasz"),
            RankingRecord(21, datetime(2021, 3, 20), "Tomasz"),
            RankingRecord(30, datetime(2020, 11, 10), "Darek"),

            RankingRecord(32, datetime(2020, 8, 1), "Tomek"),
        ),
        difficulty,
    )

    assert updated_ranking == expected_ranking
    assert updated_ranking == ranking_manager.load(difficulty)


def test_FileRankingRepo_available_difficulties():
    difficulty1 = Difficulty(4, 8)
    difficulty2 = Difficulty(4, 10)
    difficulty3 = Difficulty(3, 5)
    ranking_manager = MemoryRankingRepo()
    ranking_manager.load(difficulty1)
    ranking_manager.update(
        ScoreData(10, datetime(2020, 12, 30), difficulty2), "Tomek"
    )
    ranking_manager.update(
        ScoreData(7, datetime(2021, 4, 10), difficulty2), "Maciek"
    )
    ranking_manager.update(
        ScoreData(5, datetime(2021, 3, 2), difficulty3), "Piotrek"
    )
    assert (
        sorted(ranking_manager.available_difficulties())
        == [difficulty3, difficulty2]
    )
