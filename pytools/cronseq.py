"""Cronseq command."""


import os
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator, Optional

from croniter import croniter

from .common import ValidationException


@dataclass
class Arguments:
    """
    Arguments of `Runner`.

    :expr: cronexpr, required.
    :start: start datetime of schedule generation. Now is specified if None.
    :stop: stop datetime of schedule generation.
    :n: number of schedule generation.

    The datetime format depends on environment variable DATETIME_FORMAT.
    If it is not set, datetime format is `2006-01-02 15:04:05`.
    """

    expr: str
    start: Optional[str] = None
    stop: Optional[str] = None
    n: Optional[int] = None

    def runner(self) -> "Runner":
        """Return a new `Runner`."""
        return Runner(self)


@dataclass
class Runner:
    """Generate schedules from cronexpr.

    >>> from pytools import cronseq
    >>> args = cronseq.Arguments("0 * * * *", start="2021-07-02 00:00:00", stop="2021-07-02 05:00:00")
    >>> [str(x) for x in args.runner().run()]
    ['2021-07-02 01:00:00', '2021-07-02 02:00:00', '2021-07-02 03:00:00', '2021-07-02 04:00:00']
    """

    args: Arguments

    def run(self) -> Iterator[datetime]:
        """Run cronseq."""
        if self.args.stop is None and self.args.n is None:
            raise ValidationException("Require stop or n")
        fmt = os.environ.get("DATETIME_FORMAT", "%Y-%m-%d %H:%M:%S")
        start = (
            datetime.strptime(self.args.start, fmt)
            if self.args.start
            else datetime.now()
        )

        stop = datetime.strptime(self.args.stop, fmt) if self.args.stop else None
        count = 0

        def is_stop(c: int, t: datetime) -> bool:
            return (
                self.args.n is not None
                and c >= self.args.n
                or stop is not None
                and t >= stop
            )

        it = croniter(self.args.expr, start)
        next_time = it.get_next(datetime)
        while not is_stop(count, next_time):
            yield next_time
            count += 1
            next_time = it.get_next(datetime)
