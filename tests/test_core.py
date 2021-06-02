from bacpy.core import Difficulty, _get_ranking_path, RANKINGS_DIR


def test_get_ranking_path():
    assert _get_ranking_path(Difficulty(3, 5)) == RANKINGS_DIR / f"{3}_{5}.csv"
