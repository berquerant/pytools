"""Expand network command."""

from dataclasses import dataclass
from ipaddress import ip_network
from typing import Iterator


@dataclass
class Arguments:
    """
    Arguments of `Runner`.

    :network: CIDR.
    """

    network: str

    def runner(self) -> "Runner":
        """Return a new `Runner`."""
        return Runner(self)


@dataclass
class Runner:
    """Expand CIDR.

    >>> from pytools import expand_nw
    >>> args = expand_nw.Arguments("192.168.0.0/30")
    >>> [str(x) for x in args.runner().run()]
    ['192.168.0.0', '192.168.0.1', '192.168.0.2', '192.168.0.3']
    """

    args: Arguments

    def run(self) -> Iterator[str]:
        """Run expand_network."""
        for ip in ip_network(self.args.network, strict=True):
            yield str(ip)
