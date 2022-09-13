"""Excecutable entry point."""

import json
import sys
from argparse import ArgumentParser, Namespace
from typing import Iterator, Optional, TextIO

import pkommand

from pytools import common, jsondiff

from .log import set_debug


def join(
    files: list[str],
    target: str = "1.1-,2.1-",
    key: str = "1.1=2.1",
    delimiter: str = ",",
    verbose: bool = False,
):
    r"""
    Join files.

    key is a join condition, like "1.2=2.3", means that join the 2nd column of the source 1 and
    the 3rd column of the source 2.
    files[0] is the source 1, files[1] is the source 2.

    target is an output format, like "1.1,2.1-", means that the 1st column of the source 1 and
    the all columns of the source 2.
    Default target is the all columns.
    The syntax is:
      natural := natural number
      location := natural "." natural  // source . column
      single := location
      left := location "-"  // left limited
      right := "-" location  // right limited
      interval := location "-" location  // left and right limited
      range := interval | right | left | single
      target := range {"," range}

    e.g.
    $ cat > account.csv <<EOS
    1,account1,HR
    2,account2,Dev
    4,account4,HR
    3,account3,PR
    EOS
    $ cat > department.csv <<EOS
    10,HR,Human Resources
    12,PR,Public Relations
    11,Dev,Development
    EOS
    $ pytools join -f account.csv department.csv -d "," -k "1.3=2.2" -t "1.1-,2.1-"
    1,account1,HR,10,HR,Human Resources
    2,account2,Dev,11,Dev,Development
    4,account4,HR,10,HR,Human Resources
    3,account3,PR,12,PR,Public Relations
    $ pytools join -f account.csv department.csv -d "," -k "1.3=2.2" -t "\-1.2,2.3"
    1,account1,Human Resources
    2,account2,Development
    4,account4,Human Resources
    3,account3,Public Relations
    $ pytools join -f department.csv -d "," -k "1.3=2.2" -t "2.1,1.1,2.3" < account.csv
    10,1,Human Resources
    11,2,Development
    10,4,Human Resources
    12,3,Public Relations

    Read stdin when len(files) is 1, stdin is the source 1, the specified file is the source 2.

    $ cat > department_ext.csv <<EOS
    Development,2
    Human Resources,2b
    Public Relations,3a
    Marketing,1b
    Accounting,1a
    EOS
    $ pytools join -f department.csv -d "," -k "1.3=2.2" -t "2.1,1.1,2.3" < account.csv |\
        pytools join -f department_ext.csv -d "," -k "1.3=2.1" -t "1.1-,2.2"
    10,1,Human Resources,2b
    11,2,Development,2
    10,4,Human Resources,2b
    12,3,Public Relations,3a
    """
    set_debug(verbose)
    from pytools.join import Arguments

    def run(f: TextIO, g: TextIO):
        for row in (
            Arguments([f, g], delimiter, key, target.replace("\\", "")).runner().run()
        ):
            print(row)

    match len(files):
        case 1:
            with open(files[0]) as g:
                run(sys.stdin, g)
        case 2:
            with open(files[0]) as f, open(files[1]) as g:
                run(f, g)
        case _:
            raise common.ValidationException("Require 1 or 2 files")


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
    $ cat > right.txt <<EOS
    k2 banana
    k1 aoi
    k5 citrus
    EOS
    $ pytools mdiff -t left.txt right.txt
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


def sg(seed: str, max_matches: int = 0, perfect: bool = False):
    r"""
    Grep by set.

    e.g.
    $ (echo fire; echo water; echo ground) > set.txt
    $ pytools sg -s set.txt <<EOS
    underwater
    tree
    fire
    sky
    EOS
    underwater
    fire

    limit max match count:

    $ pytools sg -s set.txt -m 2 <<EOS
    underwater
    tree
    fire
    sky
    fire
    fire
    fire
    tree
    EOS
    underwater
    fire
    fire

    perfect match:

    $ pytools sg -s set.txt -p <<EOS
    underwater
    tree
    fire
    sky
    EOS
    fire
    """
    from pytools.setgrep import Arguments

    def read() -> Iterator[str]:
        with open(seed, "r") as f:
            for line in f:
                yield line.rstrip()

    for line in Arguments(read(), sys.stdin, max_matches, perfect).runner().run():
        print(line, end="")


def cronseq(expr: str, start: Optional[str], to: Optional[str], count: Optional[int]):
    r"""
    Expand cron expression.

    e.g.
    $ pytools cronseq -e '*/5 * * * *' -c 5
    $ pytools cronseq -e '*/19 * * * *' -s '2021-10-01 00:00:00' -t '2021-10-01 01:00:00'

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
    $ echo '192.168.0.0/30' | pytools exnw
    """
    from pytools.expand_nw import Arguments

    for line in sys.stdin:
        for x in Arguments(line.rstrip()).runner().run():
            print(x)


def ip2bin(reverse: bool):
    """
    Convert decimal ip into binary ip and vice versa.

    e.g.
    $ echo '192.168.0.1' | pytools ip2bin
    $ echo '11000000.10101000.00000000.00000001' | pytools ip2bin -r
    """
    from pytools.ip2bin import Arguments

    for line in sys.stdin:
        print(Arguments(line.rstrip(), reverse).runner().run())


def revx(separator: str = ""):
    """
    Reverse string.

    e.g.
    $ echo 'live' | pytools revx
    $ echo 'java.lang.Object' | pytools revx -s '.'
    """
    from pytools.reversex import Arguments

    for line in sys.stdin:
        print(Arguments(line.rstrip(), separator).runner().run())


def xpath(paths: list[str], raw: bool):
    """
    Select elements by xpath.

    e.g.
    $ cat sample.html | pytools xpath -p '//p[@id="alpha"]' --raw
    """
    from pytools.xpath import Arguments

    if len(paths) == 0:
        raise common.ValidationException("need at least one path")
    src = sys.stdin.read()
    for p in paths:
        for x in Arguments(src, p, raw).runner().run():
            if raw:
                print(x.raw)
                continue
            print(common.json_dumps(x.summary))


def htmldump(json: bool):
    """
    Dump html elements.

    e.g.
    $ pytools htmldump sample.html
    $ cat sample.html | pytools htmldump --json
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
    $ pytools dot -t json -o tmp.png << EOS
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
    $ pytools dot -t jsontree -o tmp.png -c l,r << EOS
    {"n":"N1","l":{"n":"N2"},"r":{"n":"N3","l":{"n":"N4"}}}
    EOS

    CSV:
    A row is a declaration of nodes and edges. The format is below:

    parent node,child node1,child node2,...

    This declares nodes, parent node, child node1, child node2, ...,
    and edges from parent node to child node1, child node2, and so on.

    e.g.
    $ pytools dot -t csv -o tmp.png << EOS
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
                if children is not None:
                    return JSONTreeDrawer(children.split(","))
                raise common.ValidationException("jsontree needs children")
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
        join,
    ]
    wrapper = pkommand.Wrapper(parser)
    for function in functions:
        wrapper.add(function)
    wrapper.run()


if __name__ == "__main__":
    main()
