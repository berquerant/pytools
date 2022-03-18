import pytest

import pytools.kvpair as kvpair


@pytest.mark.parametrize(
    "title,row,want",
    [
        (
            "empty",
            "",
            {},
        ),
        (
            "invalid format",
            "row",
            {},
        ),
        (
            "a pair",
            "k=v",
            {
                "k": "v",
            },
        ),
        (
            "pairs",
            "type=SYSCALL pid=1000",
            {
                "type": "SYSCALL",
                "pid": "1000",
            },
        ),
    ],
)
def test_run(title: str, row: str, want: dict):
    runner = kvpair.Arguments(src=[row]).runner()
    got = list(runner.run())
    assert len(got) == 1
    g = {x.key: x.value for x in got[0]}
    assert set(want.keys()) == set(g.keys())
    for k in want.keys():
        assert want[k] == g[k]
