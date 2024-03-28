"""XPath command."""

from dataclasses import dataclass
from typing import Iterator, Optional

from lxml import html


@dataclass
class Arguments:
    """
    Arguments of `Runner`.

    :source: html string.
    :xpath: xpath.
    :as_raw: yield raw html tag if True
    """

    source: str
    xpath: str
    as_raw: bool = True

    def runner(self) -> "Runner":
        """Return a new `Runner`."""
        return Runner(self)


@dataclass
class Element:
    """A result of `Runner.run()`."""

    raw: Optional[str] = None
    summary: Optional[dict] = None

    def is_raw(self) -> bool:
        """Return True if `raw` exists."""
        return self.raw is not None


@dataclass
class Runner:
    """Select elements by xpath.

    >>> from pytools import xpath
    >>> head = '<head><meta charset="utf-8"/><title>planesphere</title></head>'
    >>> stars = '<p id="alpha">Spica</p><p id="beta">Zavijava</p><p id="gamma">Porrima</p>'
    >>> body = '<body><h1 id="constellation">Virgo</h1>{}</body>'.format(stars)
    >>> src = '<html>{}{}</html>'.format(head, body)
    >>> [x.raw for x in xpath.Arguments(source=src, xpath='//p[@id="alpha"]').runner().run()]
    ['<p id="alpha">Spica</p>']
    >>> x = list(xpath.Arguments(source=src, xpath='//p[@id="alpha"]', as_raw=False).runner().run())[0].summary
    >>> x["tag"]
    'p'
    >>> x["text"]
    'Spica'
    >>> x["attrs"]["id"]
    'alpha'
    """

    args: Arguments

    def run(self) -> Iterator[Element]:
        """Run xpath. Yield `Element.raw` if `as_raw` is True."""
        contents = html.fromstring(self.args.source)
        for c in contents.xpath(self.args.xpath):
            if self.args.as_raw:
                yield Element(raw=html.tostring(c).decode().rstrip())
                continue
            yield Element(
                summary={
                    "tag": c.tag,
                    "text": c.text,
                    "attrs": dict(c.attrib),
                }
            )
