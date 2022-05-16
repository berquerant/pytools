import pytest

import pytools.setgrep as setgrep


@pytest.mark.parametrize(
    "title,args,want",
    [
        (
            "grep empty",
            setgrep.Arguments(
                target=["target"],
                source=[],
            ),
            [],
        ),
        (
            "miss",
            setgrep.Arguments(
                target=["target"],
                source=["source"],
            ),
            [],
        ),
        (
            "hit",
            setgrep.Arguments(
                target=["target"],
                source=[
                    "source",
                    "target!",
                ],
            ),
            [
                "target!",
            ],
        ),
        (
            "limit matches",
            setgrep.Arguments(
                target=["target"],
                source=["target" for _ in range(10)],
                max_matches=3,
            ),
            [
                "target",
                "target",
                "target",
            ],
        ),
        (
            "perfect",
            setgrep.Arguments(
                target=["target"],
                source=[
                    "target",
                    "targets",
                    "surtarget",
                ],
                perfect=True,
            ),
            [
                "target",
            ],
        ),
    ],
)
def test_run(title: str, args: setgrep.Arguments, want: list[str]):
    runner = args.runner()
    got = list(runner.run())
    assert "\n".join(want) == "\n".join(got), "\n".join(got)
