from typing import List

import pytest

import pytools.xpath as xpath


def __html() -> str:
    return """<html>
<head>
<meta charset="utf-8"/>
<title>planesphere</title>
</head>
<body>
<h1 id="constellation">Virgo</h1>
<p id="alpha">Spica</p>
<p id="beta">Zavijava</p>
<p id="gamma">Porrima</p>
</body>
</html>"""


@pytest.mark.parametrize(
    "title,path,want",
    [
        (
            "no candidates",
            "//Polar",
            [],
        ),
        (
            "h1",
            "//h1",
            [
                "constellation",
            ],
        ),
        (
            "p",
            "//p",
            [
                "alpha",
                "beta",
                "gamma",
            ],
        ),
    ],
)
def test_run_summary(title: str, path: str, want: List[str]):
    got = list(
        xpath.Arguments(source=__html(), xpath=path, as_raw=False).runner().run()
    )
    assert all(not x.is_raw() for x in got)
    got = [x.summary["attrs"]["id"] for x in got]
    assert len(got) == len(want), got
    assert all(g == w for g, w in zip(got, want)), got


@pytest.mark.parametrize(
    "title,path,want",
    [
        (
            "no candidates",
            "//Polar",
            [],
        ),
        (
            "h1",
            "//h1",
            [
                """<h1 id="constellation">Virgo</h1>""",
            ],
        ),
        (
            "p",
            "//p",
            [
                """<p id="alpha">Spica</p>""",
                """<p id="beta">Zavijava</p>""",
                """<p id="gamma">Porrima</p>""",
            ],
        ),
    ],
)
def test_run_raw(title: str, path: str, want: List[str]):
    got = list(xpath.Arguments(source=__html(), xpath=path).runner().run())
    assert all(x.is_raw() for x in got)
    got = [x.raw for x in got]
    assert len(got) == len(want), got
    assert all(g == w for g, w in zip(got, want)), got
