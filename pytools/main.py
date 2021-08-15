"""Excecutable entry point."""

import sys
from argparse import ArgumentParser, Namespace
from typing import Optional

import pkommand

from pytools import common, cronseq, dot, expand_nw, htmldump, ip2bin, reversex, xpath


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
    ]
    for command in commands:
        parser.add_command_class(command)
    parser.run()


if __name__ == "__main__":
    main()
