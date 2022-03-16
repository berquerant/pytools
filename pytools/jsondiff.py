"""JSONDiff command."""


from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Protocol, Tuple, Union, cast

from .common import ValidationException
from .common import json_dumps as common_json_dumps


class PathProto(Protocol):
    """Path interface."""

    def get(self, target: Any) -> Any:
        """Get an element from target."""


class PathListIndex(PathProto):
    """Path for list (array)."""

    def __init__(self, idx: int):
        """Return a new index."""
        self.idx = idx

    def get(self, target: Any) -> Any:
        """Get an element from target."""
        try:
            if isinstance(target, list):
                return target[self.idx]
            raise ValidationException("requires list")
        except Exception as e:
            raise ValidationException(f"ListIndex[{self.idx}]") from e

    def __str__(self) -> str:  # noqa: D105
        return f"[{self.idx}]"


class PathDictIndex(PathProto):
    """Path for dict (object)."""

    def __init__(self, idx: str):
        """Return a new index."""
        self.idx = idx

    def get(self, target: Any) -> Any:
        """Get an element from target."""
        try:
            if isinstance(target, dict):
                return target[self.idx]
            raise ValidationException("requires dict")
        except Exception as e:
            raise ValidationException(f"DictIndex[{self.idx}]") from e

    def __str__(self) -> str:  # noqa: D105
        return self.idx


class Path(PathProto):
    """Path impl."""

    def __init__(self, path: Optional[List[PathProto]] = None):
        """Return a new path."""
        self.path: List[PathProto] = path if path is not None else []

    @staticmethod
    def new(path: Optional[List[Union[str, int]]] = None) -> "Path":
        """Return a new path."""
        p = Path()
        if path is None:
            return p
        for x in path:
            p = p.append(x)
        return p

    def append(self, path: Union[str, int]) -> "Path":
        """Return a new path with `path` appended."""
        return Path(self.path + [self.__new_elem(path)])

    @staticmethod
    def __new_elem(path: Union[str, int]) -> PathProto:
        if isinstance(path, int):
            return PathListIndex(path)
        return PathDictIndex(path)

    def __str__(self) -> str:  # noqa: D105
        buf: List[str] = []
        for x in self.path:
            if str(x) == ".":
                continue
            if isinstance(x, PathDictIndex):
                buf.append(f".{x}")
                continue
            buf.append(str(x))
        if len(buf) == 0:
            return "."
        return "".join(buf)

    def get(self, target: Any) -> Any:
        """Get an element from target."""
        try:
            tgt = target
            for i in range(len(self.path)):
                tgt = self.__get(tgt, i)
            return tgt
        except Exception as e:
            raise ValidationException(f"Path({self})") from e

    def __get(self, target: Any, idx: int) -> Any:
        elem_path = self.path[idx]
        try:
            return elem_path.get(target)
        except Exception as e:
            raise ValidationException(f"at elem_idx[{idx}]={elem_path}") from e


def json_dumps_default(obj: Any) -> str:
    """Serialize `Path`."""
    if isinstance(obj, Path):
        return str(obj)
    raise TypeError()


def json_dumps(obj: Any) -> str:
    """Wrap json.dumps."""
    return common_json_dumps(obj, default=json_dumps_default)


@dataclass
class Diff:
    """Diff details."""

    path: Path
    reason: str
    left: Optional[Any] = None
    right: Optional[Any] = None

    def asdict(self) -> dict:
        """Conver into dict."""
        return asdict(self)


class Differ:
    """Diff detector."""

    def __init__(self, left: Any, right: Any, deep: bool = False):
        """
        Return a new `Differ`.

        :deep: compare deeply
        """
        self.left = left
        self.right = right
        self.deep = deep

    def diff(self, path: Path) -> List[Diff]:
        """Detect diffs."""
        left, right = self.__elem(path)
        if isinstance(left, list) and isinstance(right, list):
            return self.__diff_array(path, left, right)
        if isinstance(left, dict) and isinstance(right, dict):
            return self.__diff_object(
                path, cast(Dict[str, Any], left), cast(Dict[str, Any], right)
            )
        return self.__diff_elem(path, left, right)

    def __diff_array(self, path: Path, left: List[Any], right: List[Any]) -> List[Diff]:
        diffs: List[Diff] = []
        if not self.deep and len(left) != len(right):
            diffs.append(
                Diff(
                    path=path,
                    reason=f"array len {len(left)} and {len(right)}",
                    left=left,
                    right=right,
                )
            )
            return diffs

        for i in range(max(len(left), len(right))):
            p = path.append(i)
            if i >= len(left):
                diffs.append(
                    Diff(
                        path=p,
                        reason="array elem existence left is none",
                        right=right[i],
                    )
                )
                continue
            if i >= len(right):
                diffs.append(
                    Diff(
                        path=p,
                        reason="array elem existence right is none",
                        left=left[i],
                    )
                )
                continue
            diffs.extend(self.diff(p))
        return diffs

    def __diff_object(
        self, path: Path, left: Dict[str, Any], right: Dict[str, Any]
    ) -> List[Diff]:
        diffs: List[Diff] = []
        left_keys, right_keys = set(left.keys()), set(right.keys())
        if not self.deep and len(left_keys ^ right_keys) > 0:
            ldiff = sorted(list(left_keys - right_keys))
            rdiff = sorted(list(right_keys - left_keys))
            diffs.append(
                Diff(
                    path=path,
                    reason=f"keys diff {ldiff} (left-right) and {rdiff} (right-left)",
                    left=left,
                    right=right,
                )
            )
            return diffs

        for k in sorted(list(left_keys | right_keys)):
            p = path.append(k)
            if k not in left:
                diffs.append(
                    Diff(
                        path=p,
                        reason="object elem existence left is none",
                        right=right[k],
                    )
                )
                continue
            if k not in right:
                diffs.append(
                    Diff(
                        path=p,
                        reason="object elem existence right is none",
                        left=left[k],
                    )
                )
                continue
            diffs.extend(self.diff(path.append(k)))
        return diffs

    @staticmethod
    def __diff_elem(path: Path, left: Any, right: Any) -> List[Diff]:
        types = {int, str, float, str}
        for typ in types:
            if isinstance(left, typ) and isinstance(right, typ):
                if left != right:
                    return [
                        Diff(
                            path=path,
                            reason=f"value diff {typ.__name__}",
                            left=left,
                            right=right,
                        )
                    ]
                return []
        return [
            Diff(
                path=path,
                reason=f"type diff {type(left).__name__} and {type(right).__name__}",
                left=left,
                right=right,
            )
        ]

    def __elem(self, path: Path) -> Tuple[Any, Any]:
        left = path.get(self.left)
        right = path.get(self.right)
        return left, right


@dataclass
class Arguments:
    """Arguments of `Runner`."""

    left: Any
    right: Any
    deep: bool

    def runner(self) -> "Runner":
        """Return a new `Runner`."""
        return Runner(self)


@dataclass
class Runner:
    """JSONDiff."""

    args: Arguments

    def run(self) -> List[Diff]:
        """Run jsondiff."""
        return Differ(self.args.left, self.args.right, deep=self.args.deep).diff(
            Path.new()
        )
