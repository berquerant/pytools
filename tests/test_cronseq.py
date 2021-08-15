from typing import List

import pytest

import pytools.common as common
import pytools.cronseq as cronseq


def test_run_validation():
    with pytest.raises(common.ValidationException):
        cronseq.Arguments("* * * * *").runner().run().__next__()


@pytest.mark.parametrize(
    "title,args,want",
    [
        (
            "count 0",
            cronseq.Arguments("* * * * *", n=0),
            [],
        ),
        (
            "timerange 0",
            cronseq.Arguments(
                "* * * * *", start="2021-07-02 00:00:00", stop="2021-07-02 00:00:00"
            ),
            [],
        ),
        (
            "count 1",
            cronseq.Arguments("* * * * *", start="2021-07-02 00:00:00", n=1),
            [
                "2021-07-02 00:01:00",
            ],
        ),
        (
            "count 2",
            cronseq.Arguments("* * * * *", start="2021-07-02 00:00:00", n=2),
            [
                "2021-07-02 00:01:00",
                "2021-07-02 00:02:00",
            ],
        ),
        (
            "timerange",
            cronseq.Arguments(
                "* * * * *", start="2021-07-02 00:00:00", stop="2021-07-02 00:02:00"
            ),
            [
                "2021-07-02 00:01:00",
            ],
        ),
        (
            "now",
            cronseq.Arguments("0 * * * *", n=3),
            [
                "2021-07-02 13:00:00",
                "2021-07-02 14:00:00",
                "2021-07-02 15:00:00",
            ],
        ),
    ],
)
@pytest.mark.freeze_time("2021-07-02 12:30:00")
def test_run(title: str, args: cronseq.Arguments, want: List[str]):
    runner = args.runner()
    got = [str(x) for x in list(runner.run())]
    assert len(got) == len(want), got
    assert all(g == w for g, w in zip(got, want)), got
