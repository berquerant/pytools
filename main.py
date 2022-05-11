"""Excecutable entry point."""

import json
import sys
from argparse import ArgumentParser, Namespace
from typing import Optional

import pkommand

from pytools import common, jsondiff


def kvpair():
    """
    Key-Value pair to json.

    e.g.
    $ echo 'type=SYSCALL msg=audit(1603703472.072:784): arch=c000003e syscall=2 success=no exit=-13' | pytools kvpair
    {"arch":"c000003e","exit":"-13","msg":"audit(1603703472.072:784):","success":"no","syscall":"2","type":"SYSCALL"}
    """
    from pytools.kvpair import Arguments

    for row in Arguments(x.rstrip() for x in sys.stdin).runner().run():
        print(common.json_dumps({x.key: x.value for x in row}))


class JSONDiffCommand(pkommand.Command):  # noqa: D101
    @staticmethod
    def name() -> str:  # noqa: D102
        return "jsondiff"

    @classmethod
    def help(cls) -> str:  # noqa: D102
        return r"""Diff json.

e.g.
$ (echo '{"l":{"k":1},"r":{"k":2,"v":3}}';echo '{"l":{"k":2,"v":"3"},"r":{"k":2,"v":3}}') | pytools jsondiff
{"diff":[{"left":1,"path":".k","reason":"value diff int","right":2},{"left":null,"path":".v","reason":"object elem existence left is none","right":3}],"line":1}
{"diff":[{"left":"3","path":".v","reason":"type diff str and int","right":3}],"line":2}
"""  # noqa: E501

    @classmethod
    def register(cls, parser: ArgumentParser):  # noqa: D102
        parser.add_argument(
            "-s", "--shallow", action="store_true", help="shallow equality"
        )
        parser.add_argument(
            "-l", "--left", action="store", type=str, default="l", help="left key"
        )
        parser.add_argument(
            "-r", "--right", action="store", type=str, default="r", help="right key"
        )
        parser.add_argument(
            "-1",
            "--oneshot",
            action="store_true",
            help="read json from stdin only once",
        )
        parser.add_argument("files", nargs="*", type=str, help="files, 0 or 2 files")

    @staticmethod
    def __new_runner(args: Namespace, src: str) -> jsondiff.Runner:
        js = json.loads(src)
        left = js[args.left]
        right = js[args.right]
        return jsondiff.Arguments(
            left=left, right=right, deep=not args.shallow
        ).runner()

    def __oneshot(self, args: Namespace):
        diffs = self.__new_runner(args, sys.stdin.read()).run()
        if diffs:
            print(jsondiff.json_dumps(diffs))

    @staticmethod
    def __files(args: Namespace):
        if len(args.files) != 2:
            raise common.ValidationException(
                f"requires 2 files but given {len(args.files)}"
            )
        with open(args.files[0]) as lf, open(args.files[1]) as rf:
            left = json.load(lf)
            right = json.load(rf)
        diffs = (
            jsondiff.Arguments(left=left, right=right, deep=not args.shallow)
            .runner()
            .run()
        )
        if diffs:
            print(jsondiff.json_dumps(diffs))

    def __lines(self, args: Namespace):
        for i, line in enumerate(sys.stdin):
            try:
                diffs = self.__new_runner(args, line).run()
                if diffs:
                    print(
                        jsondiff.json_dumps(
                            {
                                "line": i + 1,
                                "diff": diffs,
                            }
                        )
                    )
            except Exception as e:
                raise common.ValidationException(f"line {i + 1}") from e

    def run(self, args: Namespace):  # noqa: D102
        if args.oneshot:
            self.__oneshot(args)
            return
        if args.files:
            self.__files(args)
            return
        self.__lines(args)


def csvcut(
    field: str,
    delimiter: str = ",",
    headers: Optional[str] = None,
    include_headers: bool = False,
    as_json: bool = False,
):
    """
    Cut csv.

    e.g.
    $ pytools csvcut -f '1,3-' <<EOS
    1,cmd,cronseq
    2,revx
    3,mapdiff,diff,md
    EOS
    1,cronseq
    2
    3,diff,md
    """
    from pytools.csvcut import Arguments

    Arguments(
        field, sys.stdin, sys.stdout, include_headers, headers, delimiter, as_json
    ).runner().run()


def mdiff(
    target: list[str], key: int = 0, delim: str = " ", with_no_diff: bool = False
):
    r"""
    Diff by key.
    e.g.
    $ cat > left.txt <<EOS
    k1 apple
    k2 banana
    k3 citrus
    k4 dragon fruit
    EOS
    cat > right.txt <<EOS
    k2 banana
    k1 aoi
    k5 citrus
    EOS
    $ pytools mdiff left.txt right.txt
    > k5 citrus
    < k4 dragon fruit
    < k3 citrus
    <>< k1 apple
    <>> k1 aoi
    """
    from pytools.mapdiff import Arguments

    if len(target) < 2:
        raise common.ValidationException("need at least two targets")
    lfile, rfile = target[0], target[1]
    with open(lfile) as left, open(rfile) as right:
        for line in Arguments(left, right, key, delim, with_no_diff).runner().run():
            print(line)


def sg(seed: str):
    r"""
    Grep by set.

    e.g.
    $ (echo fire; echo water; echo ground) > set.txt
    $ pytools sg set.txt <<EOS
    underwater
    tree
    fire
    sky
    EOS
    underwater
    fire
    """
    from pytools.setgrep import Arguments

    with open(seed, "r") as f:
        src = f.readlines()
    for line in Arguments(src, sys.stdin).runner().run():
        print(line, end="")


def cronseq(expr: str, start: Optional[str], to: Optional[str], count: Optional[int]):
    r"""
    Expand cron expression.

    e.g.
    pytools cronseq -e '*/5 * * * *' -c 5
    pytools cronseq -e '*/19 * * * *' -s '2021-10-01 00:00:00' -t '2021-10-01 01:00:00'

    note:
    The datetime format depends on environment variable DATETIME_FORMAT.
    If it is not set, the format is `2006-01-02 15:04:05`.
    """
    from pytools.cronseq import Arguments

    for x in Arguments(expr, start, to, count).runner().run():
        print(x)


def exnw():
    """
    Expand CIDR.

    e.g.
    echo '192.168.0.0/30' | pytools exnw
    """
    from pytools.expand_nw import Arguments

    for line in sys.stdin:
        for x in Arguments(line.rstrip()).runner().run():
            print(x)


def ip2bin(reverse: bool):
    """
    Convert decimal ip into binary ip and vice versa.

    e.g.
    echo '192.168.0.1' | pytools ip2bin
    echo '11000000.10101000.00000000.00000001' | pytools ip2bin -r
    """
    from pytools.ip2bin import Arguments

    for line in sys.stdin:
        print(Arguments(line.rstrip(), reverse).runner().run())


def revx(separator: Optional[str]):
    """
    Reverse string.

    e.g.
    echo 'live' | pytools revx
    echo 'java.lang.Object' | pytools revx -s '.'
    """
    from pytools.reversex import Arguments

    for line in sys.stdin:
        print(Arguments(line.rstrip(), separator).runner().run())


def xpath(paths: list[str], raw: bool):
    """
    Select elements by xpath.

    e.g.
    cat sample.html | pytools xpath -p '//p[@id="alpha"]' --raw
    """
    from pytools.xpath import Arguments

    if len(paths) == 0:
        raise common.ValidationException("need at least one path")
    for p in paths:
        for x in Arguments(sys.stdin, p, raw).runner().run():
            if raw:
                print(x.raw)
                continue
            print(common.json_dumps(x.summary))


def htmldump(json: bool):
    """
    Dump html elements.

    e.g.
    pytools htmldump sample.html
    cat sample.html | pytools htmldump --json
    """
    from pytools.htmldump import Arguments

    for x in Arguments(sys.stdin, json).runner().run():
        print(x)


def dot(output: str, type: str, children: Optional[str]):
    """
    Render graph.

    JSON:
    A row is a declaration of a node and the edges from it. The format is below:

    {
      "id": "node id",
      "to": [edge],
      "other info": ...,
      ...
    }

    The label of a node is below:

    {
      "id": "node id",
      "other info": ...,
      ...
    }

    The format of an edge is below:

    {
      "id": "destination node id",
      "el": "edge label"
    }

    e.g.
    pytools dot -t json -o tmp.png << EOS
    {"id":"A","to":[{"id":"B","el":"ab"}],"comment":"Alpha"}
    {"id":"B","to":[{"id":"C","el":"bc"}]}
    {"id":"C","to":[{"id":"A","el":"ca"},{"id":"C","el":"cc"}]}
    EOS

    JSONTree:
    Regard an object as a declaration of a node and edges from it to the children objects.
    This is just for drawing a tree. The format is below:

    {
      "child key1": {...},
      "child key2": {...},
      ...,
      "other info1": ...,
      "other info2": ...,
      ...
    }

    The label of a node is below:

    {
      "other info1": ...,
      "other info2": ...,
      ...
    }

    The node has edges to child key1 object, child key2 object, and other children objects,
    their labels are their keys, the object under other info1 has an edge from the parent with "other info1" label.

    e.g.
    pytools dot -t jsontree -o tmp.png -c l,r << EOS
    {"n":"N1","l":{"n":"N2"},"r":{"n":"N3","l":{"n":"N4"}}}
    EOS

    CSV:
    A row is a declaration of nodes and edges. The format is below:

    parent node,child node1,child node2,...

    This declares nodes, parent node, child node1, child node2, ...,
    and edges from parent node to child node1, child node2, and so on.

    e.g.
    pytools dot -t csv -o tmp.png << EOS
    A,B
    B,C
    C,A,C
    EOS
    """
    from pytools.dot import Arguments, CSVDrawer, Drawer, JSONDrawer, JSONTreeDrawer

    def select_drawer() -> Drawer:
        match type:
            case "json":
                return JSONDrawer()
            case "jsontree":
                return JSONTreeDrawer(children.split(","))
            case "csv":
                return CSVDrawer()
            case _:
                raise common.ValidationException(f"invalid type {type}")

    r = Arguments(sys.stdin, output, select_drawer()).runner().run()
    print(r)


def main():
    """Entry point."""
    commands = [
        JSONDiffCommand,
    ]
    parser = pkommand.Parser("pytools")
    for command in commands:
        parser.add_command_class(command)

    functions = [
        dot,
        csvcut,
        mdiff,
        sg,
        cronseq,
        exnw,
        ip2bin,
        revx,
        xpath,
        htmldump,
        kvpair,
    ]
    wrapper = pkommand.Wrapper(parser)
    for function in functions:
        wrapper.add(function)
    wrapper.run()


if __name__ == "__main__":
    main()
