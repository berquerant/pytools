"""Excecutable entry point."""

import json
import sys
from argparse import ArgumentParser, Namespace
from typing import Iterator, Optional

import pkommand

from pytools import (
    common,
    cronseq,
    csvcut,
    dot,
    expand_nw,
    htmldump,
    ip2bin,
    jsondiff,
    mapdiff,
    reversex,
    setgrep,
    xpath,
)


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

    def __new_runner(self, args: Namespace, src: str) -> jsondiff.Runner:
        js = json.loads(src)
        left = js[args.left]
        right = js[args.right]
        return jsondiff.Arguments(
            left=left, right=right, deep=not args.shallow
        ).runner()

    def __oneshot(self, args: Namespace):
        diffs = self.__new_runner(args, sys.stdin.read()).run()
        if diffs:
            print(jsondiff.json_dumps([x.asdict() for x in diffs]))

    def __files(self, args: Namespace):
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
            print(jsondiff.json_dumps([x.asdict() for x in diffs]))

    def __lines(self, args: Namespace):
        for i, line in enumerate(sys.stdin):
            try:
                diffs = self.__new_runner(args, line).run()
                if diffs:
                    print(
                        jsondiff.json_dumps(
                            {
                                "line": i + 1,
                                "diff": [x.asdict() for x in diffs],
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


class CSVCutCommand(pkommand.Command):  # noqa: D101
    @staticmethod
    def name() -> str:  # noqa: D102
        return "csvcut"

    @classmethod
    def help(cls) -> str:  # noqa: D102
        return r"""Cut csv.

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

    @classmethod
    def register(cls, parser: ArgumentParser):  # noqa: D102
        parser.add_argument(
            "-f",
            "--field",
            action="store",
            type=str,
            required=True,
            help="target expression. like 1-3,5",
        )
        parser.add_argument(
            "-d",
            "--delimiter",
            action="store",
            default=",",
            help="delimiter for output.",
        )
        parser.add_argument(
            "-l", "--headers", action="store", help="headers for output. like h1,h2,h3"
        )
        parser.add_argument(
            "-i",
            "--headers_included",
            action="store_true",
            help="if true, use the first row as headers",
        )
        parser.add_argument(
            "-j", "--as_json", action="store_true", help="if true, output as json"
        )

    def run(self, args: Namespace):  # noqa: D102
        csvcut.Arguments(
            target=args.field,
            source=sys.stdin,
            destination=sys.stdout,
            headers_included=args.headers_included,
            headers=args.headers,
            delimiter=args.delimiter,
            as_json=args.as_json,
        ).runner().run()


class MapDiffCommand(pkommand.Command):  # noqa: D101
    @staticmethod
    def name() -> str:  # noqa: D102
        return "mapdiff"

    @classmethod
    def help(cls) -> str:  # noqa: D102
        return r"""Diff by key.
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
$ pytools mapdiff left.txt right.txt
> k5 citrus
< k4 dragon fruit
< k3 citrus
<>< k1 apple
<>> k1 aoi"""

    @classmethod
    def register(cls, parser: ArgumentParser):  # noqa: D102
        parser.add_argument(
            "targets", metavar="FILE", type=str, nargs=2, help="target files"
        )
        parser.add_argument(
            "-k",
            "--key",
            action="store",
            type=int,
            default=0,
            help="key field (zero origin)",
        )
        parser.add_argument(
            "-d",
            "--delim",
            action="store",
            type=str,
            default=" ",
            help="field delimiter character",
        )
        parser.add_argument(
            "-w",
            "--with_no_diff",
            action="store_true",
            help="if true, print line even if no diff",
        )

    def run(self, args: Namespace):  # noqa: D102
        left_file, right_file = args.targets[0], args.targets[1]
        with open(left_file) as left, open(right_file) as right:
            runner = mapdiff.Arguments(
                left=left,
                right=right,
                key=args.key,
                delimiter=args.delim,
                with_no_diff=args.with_no_diff,
            ).runner()
            for line in runner.run():
                print(line)


class SetGrepCommand(pkommand.Command):  # noqa: D101
    @staticmethod
    def name() -> str:  # noqa: D102
        return "setgrep"

    @classmethod
    def help(cls) -> str:  # noqa: D102
        return r"""Grep by set.

e.g.
$ (echo fire; echo water; echo ground) > set.txt
$ pytools setgrep set.txt <<EOS
underwater
tree
fire
sky
EOS
underwater
fire"""

    @classmethod
    def register(cls, parser: ArgumentParser):  # noqa: D102
        parser.add_argument(
            "seeds", metavar="SEED", type=str, nargs="+", help="seed files"
        )

    def run(self, args: Namespace):  # noqa: D102
        def chain_source() -> Iterator[str]:
            for name in args.seeds:
                with open(name, "r") as f:
                    yield from f

        runner = setgrep.Arguments(target=chain_source(), source=sys.stdin).runner()
        for line in runner.run():
            print(line, end="")


class CronSeqCommand(pkommand.Command):  # noqa: D101
    @staticmethod
    def name() -> str:  # noqa: D102
        return "cronseq"

    @classmethod
    def help(cls) -> str:  # noqa: D102
        return r"""Expand cron expression.

e.g.
pytools cronseq -e '*/5 * * * *' -n 5
pytools cronseq -e '*/19 * * * *' -s '2021-10-01 00:00:00' -t '2021-10-01 01:00:00'

note:
The datetime format depends on environment variable DATETIME_FORMAT.
If it is not set, the format is `2006-01-02 15:04:05`."""

    @classmethod
    def register(cls, parser: ArgumentParser):  # noqa: D102
        parser.add_argument(
            "-e",
            "--expr",
            action="store",
            type=str,
            required=True,
            help="cron expression.",
        )
        parser.add_argument(
            "-s",
            "--start",
            action="store",
            type=str,
            help="start datetime of schedule generation. Now is specified if not specified.",
        )
        parser.add_argument(
            "-t",
            "--stop",
            action="store",
            type=str,
            help="stop datetime of schedule generation.",
        )
        parser.add_argument(
            "-n",
            "--count",
            action="store",
            type=int,
            help="number of schedule generation.",
        )

    def run(self, args: Namespace):  # noqa: D102
        for v in (
            cronseq.Arguments(args.expr, args.start, args.stop, args.count)
            .runner()
            .run()
        ):
            print(v)


class ExpandNetworkCommand(pkommand.Command):  # noqa: D101
    @staticmethod
    def name() -> str:  # noqa: D102
        return "expand_nw"

    @classmethod
    def help(cls) -> str:  # noqa: D102
        return """Expand CIDR.

e.g.
pytools expand_nw '192.168.0.0/30'
echo '192.168.0.0/30' | pytools expand_nw"""

    @classmethod
    def register(cls, parser: ArgumentParser):  # noqa: D102
        parser.add_argument("networks", metavar="N", type=str, nargs="*", help="CIDR.")

    def run(self, args: Namespace):  # noqa: D102
        def inner(nw: str):
            for v in expand_nw.Arguments(nw).runner().run():
                print(v)

        if args.networks:
            for network in args.networks:
                inner(network)
            return
        for line in sys.stdin:
            inner(line.rstrip())


class IP2BinCommand(pkommand.Command):  # noqa: D101
    @staticmethod
    def name() -> str:  # noqa: D102
        return "ip2bin"

    @classmethod
    def help(cls) -> str:  # noqa: D102
        return """Convert decimal ip into binary ip and vice versa.

e.g.
pytools ip2bin '192.168.0.1'
echo '192.168.0.1' | pytools ip2bin
pytools ip2bin '11000000.10101000.00000000.00000001' -r"""

    @classmethod
    def register(cls, parser: ArgumentParser):  # noqa: D102
        parser.add_argument(
            "targets", metavar="T", type=str, nargs="*", help="ip address."
        )
        parser.add_argument(
            "-r", "--reverse", action="store_true", help="bin2ip if true."
        )

    def run(self, args: Namespace):  # noqa: D102
        if args.targets:
            for target in args.targets:
                print(ip2bin.Arguments(target, args.reverse).runner().run())
            return
        for line in sys.stdin:
            print(ip2bin.Arguments(line.rstrip(), args.reverse).runner().run())


class ReverseXCommand(pkommand.Command):  # noqa: D101
    @staticmethod
    def name() -> str:  # noqa: D102
        return "revx"

    @classmethod
    def help(cls) -> str:  # noqa: D102
        return """Reverse string.

e.g.
pytools revx 'live'
echo 'live' | pytools revx
pytools revx 'java.lang.Object' -s '.'"""

    @classmethod
    def register(cls, parser: ArgumentParser):  # noqa: D102
        parser.add_argument(
            "targets", metavar="T", type=str, nargs="*", help="target string."
        )
        parser.add_argument(
            "-s",
            "--separator",
            action="store",
            type=str,
            help="field separator character.",
        )

    def run(self, args: Namespace):  # noqa: D102
        if args.targets:
            for target in args.targets:
                print(reversex.Arguments(target, args.separator).runner().run())
            return
        for line in sys.stdin:
            print(reversex.Arguments(line.rstrip(), args.separator).runner().run())


class XPathCommand(pkommand.Command):  # noqa: D101
    @staticmethod
    def name() -> str:  # noqa: D102
        return "xpath"

    @classmethod
    def help(cls) -> str:  # noqa: D102
        return """Select elements by xpath.

e.g.
pytools xpath -f sample.html '//p[@id="alpha"]'
cat sample.html | pytools xpath '//p[@id="alpha"]' -r"""

    @classmethod
    def register(cls, parser: ArgumentParser):  # noqa: D102
        parser.add_argument(
            "-f", "--source", action="store", type=str, help="source file."
        )
        parser.add_argument("xpaths", metavar="X", type=str, nargs="+", help="xpath,")
        parser.add_argument(
            "-r", "--raw", action="store_true", help="print raw html tag if true."
        )

    @staticmethod
    def __read_source(filename: Optional[str]) -> str:
        if filename:
            with open(filename, "r") as f:
                return f.read()
        return sys.stdin.read()

    def run(self, args: Namespace):  # noqa: D102
        source = self.__read_source(args.source)
        for x in args.xpaths:
            for v in xpath.Arguments(source, x, args.raw).runner().run():
                if v.is_raw():
                    print(v.raw)
                    continue
                print(common.json_dumps(v.summary, sort_keys=True))


class HTMLDumpCommand(pkommand.Command):  # noqa: D101
    @staticmethod
    def name() -> str:  # noqa: D102
        return "htmldump"

    @classmethod
    def help(cls) -> str:  # noqa: D102
        return """Dump html elements.

e.g.
pytools htmldump sample.html
cat sample.html | pytools htmldump -j"""

    @classmethod
    def register(cls, parser: ArgumentParser):  # noqa: D102
        parser.add_argument(
            "sources", metavar="S", type=str, nargs="*", help="html sources."
        )
        parser.add_argument(
            "-j", "--json", action="store_true", help="print as json if true else tsv."
        )

    def run(self, args: Namespace):  # noqa: D102
        if args.sources:
            for source in args.sources:
                with open(source, "r") as f:
                    for v in htmldump.Arguments(f, args.json).runner().run():
                        print(v)
            return
        for v in htmldump.Arguments(sys.stdin, args.json).runner().run():
            print(v)


class DotCommand(pkommand.Command):  # noqa: D101
    @staticmethod
    def name() -> str:  # noqa: D102
        return "dot"

    @classmethod
    def help(cls) -> str:  # noqa: D102
        return """Render graph.

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
EOS"""

    @classmethod
    def register(cls, parser: ArgumentParser):  # noqa: D102
        parser.add_argument(
            "-f", "--source", action="store", type=str, help="source file."
        )
        parser.add_argument(
            "-o",
            "--destination",
            action="store",
            type=str,
            required=True,
            help="filname for saving image.",
        )
        parser.add_argument(
            "-t",
            "--draw_type",
            choices=["json", "jsontree", "csv"],
            required=True,
            help="input format.",
        )
        parser.add_argument(
            "-c",
            "--children",
            action="store",
            type=str,
            help="children of jsontree, csv.",
        )

    @staticmethod
    def __drawer(args: Namespace) -> dot.Drawer:
        draw_type = args.draw_type
        if draw_type == "json":
            return dot.JSONDrawer()
        if draw_type == "jsontree":
            return dot.JSONTreeDrawer(args.children.split(","))
        if draw_type == "csv":
            return dot.CSVDrawer()
        raise common.ValidationException("invalid draw_type {}".format(draw_type))

    def run(self, args: Namespace):  # noqa: D102
        drawer = self.__drawer(args)
        if args.source:
            with open(args.source, "r") as f:
                print(dot.Arguments(f, args.destination, drawer).runner().run())
                return
        print(dot.Arguments(sys.stdin, args.destination, drawer).runner().run())


def main():
    """Entry point."""
    parser = pkommand.Parser("pytools")
    commands = [
        CronSeqCommand,
        ExpandNetworkCommand,
        IP2BinCommand,
        ReverseXCommand,
        XPathCommand,
        HTMLDumpCommand,
        DotCommand,
        SetGrepCommand,
        MapDiffCommand,
        CSVCutCommand,
        JSONDiffCommand,
    ]
    for command in commands:
        parser.add_command_class(command)
    parser.run()


if __name__ == "__main__":
    main()
