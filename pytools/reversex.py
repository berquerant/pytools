"""ReverseX command."""

from dataclasses import dataclass


@dataclass
class Arguments:
    """
    Arguments of `Runner`.

    :target: string.
    :separator: field separator character.
    """

    target: str
    separator: str = ""

    def runner(self) -> "Runner":
        """Return a new `Runner`."""
        return Runner(self)


@dataclass
class Runner:
    """Reverse string.

    >>> from pytools import reversex
    >>> reversex.Arguments(target="live").runner().run()
    'evil'
    >>> reversex.Arguments(target="java.lang.Object", separator=".").runner().run()
    'Object.lang.java'
    """

    args: Arguments

    def run(self) -> str:
        """Run reversex."""
        if self.args.separator:
            return self.args.separator.join(
                reversed(self.args.target.split(self.args.separator))
            )
        return "".join(reversed(self.args.target))
