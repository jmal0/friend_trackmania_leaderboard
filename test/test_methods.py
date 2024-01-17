import pytest
import friend_trackmania_leaderboard.main as _main


def test_sum_trophy_points():
    with pytest.raises(ValueError):
        _main._sum_trophy_points([])

    assert _main._sum_trophy_points([1, 0, 0, 0, 0, 0, 0, 0, 0]) == 1
    assert _main._sum_trophy_points([0, 1, 0, 0, 0, 0, 0, 0, 0]) == 10
    assert _main._sum_trophy_points([0, 0, 1, 0, 0, 0, 0, 0, 0]) == 100
    assert _main._sum_trophy_points([0, 0, 0, 1, 0, 0, 0, 0, 0]) == 1000
    assert _main._sum_trophy_points([0, 0, 0, 0, 1, 0, 0, 0, 0]) == 10000
    assert _main._sum_trophy_points([0, 0, 0, 0, 0, 1, 0, 0, 0]) == 100000
    assert _main._sum_trophy_points([0, 0, 0, 0, 0, 0, 1, 0, 0]) == 1000000
    assert _main._sum_trophy_points([0, 0, 0, 0, 0, 0, 0, 1, 0]) == 10000000
    assert _main._sum_trophy_points([0, 0, 0, 0, 0, 0, 0, 0, 1]) == 100000000

    assert _main._sum_trophy_points([5, 13, 18, 0, 0, 0, 0, 0, 0]) == 1935
    assert _main._sum_trophy_points([0, 0, 0, 4, 0, 0, 0, 0, 0]) == 4000
