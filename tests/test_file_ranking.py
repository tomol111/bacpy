import pytest

from bacpy.file_ranking import FileRankingRepo
from tests.ranking import BaseTest_RankingRepo


# TODO: test backward compatibility by snapshotting file


@pytest.fixture
def ranking_repo(tmp_path):
    return FileRankingRepo(tmp_path)


class Test_FileRankingRepo(BaseTest_RankingRepo):
    pass
