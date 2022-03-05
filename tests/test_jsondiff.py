import json
from typing import Any, List

import pytest

import pytools.jsondiff as jsondiff


@pytest.mark.parametrize(
    "title,differ,diff_paths",
    [
        (
            "empty objs",
            jsondiff.Differ(
                {},
                {},
            ),
            [],
        ),
        (
            "objs diff",
            jsondiff.Differ(
                {},
                {
                    "k": "v",
                },
            ),
            [jsondiff.Path.new()],
        ),
        (
            "objs diff deep",
            jsondiff.Differ(
                {},
                {
                    "k": "v",
                },
                deep=True,
            ),
            [
                jsondiff.Path.new(["k"]),
            ],
        ),
        (
            "objs no diff",
            jsondiff.Differ(
                {
                    "k": "v",
                },
                {
                    "k": "v",
                },
            ),
            [],
        ),
        (
            "nested diff",
            jsondiff.Differ(
                {
                    "t": {
                        "k1": "v1",
                        "k2": {
                            "s": "str",
                        },
                        "k3": [
                            1,
                            True,
                        ],
                    },
                },
                {
                    "t": {
                        "k2": {
                            "s": "str",
                            "v": 1.2,
                        },
                        "k3": [
                            0,
                            True,
                            False,
                        ],
                        "k4": 1000,
                    },
                },
                deep=True,
            ),
            [
                jsondiff.Path.new(["t", "k1"]),  # t.k1 exist
                jsondiff.Path.new(["t", "k2", "v"]),  # t.k2.v exist
                jsondiff.Path.new(["t", "k3", 0]),  # t.k3[0] value
                jsondiff.Path.new(["t", "k3", 2]),  # t.k3[2] exist
                jsondiff.Path.new(["t", "k4"]),  # t.k4 exist
            ],
        ),
        (
            "empty arrays",
            jsondiff.Differ(
                [],
                [],
            ),
            [],
        ),
        (
            "arrays diff",
            jsondiff.Differ(
                [],
                [1],
            ),
            [jsondiff.Path.new()],  # top level
        ),
        (
            "arrays no diff",
            jsondiff.Differ(
                [1],
                [1],
            ),
            [],
        ),
        (
            "arrays diffs",
            jsondiff.Differ(
                [1, 2, 3],
                [2, 2, 1],
            ),
            [
                jsondiff.Path.new([0]),
                jsondiff.Path.new([2]),
            ],
        ),
        (
            "arrays len",
            jsondiff.Differ(
                [1],
                [1, 1],
            ),
            [jsondiff.Path.new()],
        ),
        (
            "arrays len deep",
            jsondiff.Differ(
                [1],
                [1, 1],
                deep=True,
            ),
            [
                jsondiff.Path.new([1]),
            ],
        ),
    ],
)
def test_diff(
    title: str,
    differ: jsondiff.Differ,
    diff_paths: List[jsondiff.Path],
):
    got = differ.diff(jsondiff.Path.new())
    got_len = len(got)
    want_len = len(diff_paths)
    assert got_len == want_len, f"diff len {want_len} {got_len}"
    if want_len != got_len:
        return
    for i in range(want_len):
        w = diff_paths[i]
        g = got[i].path
        assert str(w) == str(g), f"diff_path[{i}] {w} {g.path} ({g.reason})"


@pytest.mark.parametrize(
    "title,target,path,want",
    [
        (
            "no paths",
            1,
            jsondiff.Path.new(),
            1,
        ),
        (
            "obj",
            {
                "key": 1,
                "other": 2,
            },
            jsondiff.Path.new(["key"]),
            1,
        ),
        (
            "array",
            [1, 2],
            jsondiff.Path.new([0]),
            1,
        ),
        (
            "obj.obj",
            {
                "key": {
                    "internal": 1,
                    "other": 2,
                },
            },
            jsondiff.Path.new(["key", "internal"]),
            1,
        ),
        (
            "obj.array",
            {
                "key": [
                    1,
                    2,
                ],
                "other": "val",
            },
            jsondiff.Path.new(["key", 1]),
            2,
        ),
        (
            "array.obj",
            [
                {
                    "key": {
                        "mic": 1,
                    },
                    "other": 100,
                },
            ],
            jsondiff.Path.new([0, "key"]),
            {
                "mic": 1,
            },
        ),
    ],
)
def test_path(
    title: str,
    target: Any,
    path: jsondiff.Path,
    want: Any,
):
    got = path.get(target)
    got_json = json.dumps(got, separators=(".", ":"), sort_keys=True)
    want_json = json.dumps(want, separators=(".", ":"), sort_keys=True)
    assert want_json == got_json, title


@pytest.mark.parametrize(
    "title,path,want",
    [
        (
            "empty",
            jsondiff.Path.new(),
            ".",
        ),
        (
            "key",
            jsondiff.Path.new(["k"]),
            ".k",
        ),
        (
            "idx",
            jsondiff.Path.new([1]),
            "[1]",
        ),
        (
            "key.idx",
            jsondiff.Path.new(["k", 2]),
            ".k[2]",
        ),
        (
            "idx.key",
            jsondiff.Path.new([10, "k"]),
            "[10].k",
        ),
        (
            "key.idx.idx",
            jsondiff.Path.new(["k", 2, 3]),
            ".k[2][3]",
        ),
    ],
)
def test_path_str(
    title: str,
    path: jsondiff.Path,
    want: str,
):
    assert str(path) == want
