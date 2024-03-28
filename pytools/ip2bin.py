"""IP2bin command."""

from dataclasses import dataclass


@dataclass
class Arguments:
    """
    Arguments of `Runner`.

    :target: ip address.
    :reverse: bin2ip if True.
    """

    target: str
    reverse: bool = False

    def runner(self) -> "Runner":
        """Return a new `Runner`."""
        return Runner(self)


@dataclass
class Runner:
    """IP2bin or Bin2ip.

    >>> from pytools import ip2bin
    >>> ip2bin.Arguments(target="192.168.0.1").runner().run()
    '11000000.10101000.00000000.00000001'
    >>> ip2bin.Arguments(target="11000000.10101000.00000000.00000001", reverse=True).runner().run()
    '192.168.0.1'
    """

    args: Arguments

    def run(self) -> str:
        """Run ip2bin."""
        if self.args.reverse:
            return ".".join(str(int(x, 2)) for x in self.args.target.split("."))
        return ".".join("{:08b}".format(int(x)) for x in self.args.target.split("."))
