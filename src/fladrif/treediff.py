# Copyright 2010 Stefan Merten
# Copyright 2023 Sam Wilson
#
# fladrif is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published
# by the Free Software Foundation; either version 2 of the License,
# or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.

from abc import ABC, abstractmethod
from collections import deque
from contextlib import contextmanager
from difflib import SequenceMatcher
from enum import IntEnum, auto
from typing import (
    Final,
    Generic,
    Iterator,
    List,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
)

N = TypeVar("N")


class Adapter(ABC, Generic[N]):
    def deep_equals(self, lhs: N, rhs: N) -> bool:
        if lhs is rhs:
            return True

        if not self.shallow_equals(lhs, rhs):
            return False

        stack = deque([(self.children(lhs), self.children(rhs))])

        while stack:
            lefts, rights = stack.popleft()
            if len(lefts) != len(rights):
                return False

            for left, right in zip(lefts, rights):
                if not self.shallow_equals(left, right):
                    return False
                stack.append((self.children(left), self.children(right)))

        return True

    def deep_hash(self, node: N) -> int:
        # TODO: This is not an ideal way to calculate hashes.

        value = 0
        count = 0
        stack = [(0, node)]

        while stack:
            (depth, current) = stack.pop()
            count += 1

            value ^= hash((depth, count, self.shallow_hash(current)))

            for child in self.children(current):
                stack.append((depth + 1, child))

        return value

    @abstractmethod
    def shallow_equals(self, lhs: N, rhs: N) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def shallow_hash(self, node: N) -> int:
        raise NotImplementedError()

    @abstractmethod
    def children(self, node: N) -> Sequence[N]:
        raise NotImplementedError()


class _Wrap(ABC, Generic[N]):
    __slots__ = ("_hash", "adapter", "node")

    _hash: Optional[int]

    def __init__(self, adapter: Adapter[N], node: N) -> None:
        self.node: Final[N] = node
        self.adapter: Final[Adapter[N]] = adapter
        self._hash = None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented

        if self._hash is not None and other._hash is not None:
            if self._hash != other._hash:
                return False

        return self.eq(other.node)

    def __hash__(self) -> int:
        if self._hash is None:
            value = self.hash()
            self._hash = value
            return value

        return self._hash

    def __ne__(self, other: object) -> bool:
        eq = self.__eq__(other)
        if eq == NotImplemented:
            return NotImplemented
        return not eq

    @abstractmethod
    def hash(self) -> int:
        raise NotImplementedError()

    @abstractmethod
    def eq(self, other: N) -> bool:
        raise NotImplementedError()


class _Shallow(Generic[N], _Wrap[N]):
    def hash(self) -> int:
        return self.adapter.shallow_hash(self.node)

    def eq(self, other: N) -> bool:
        return self.adapter.shallow_equals(self.node, other)


class _Deep(Generic[N], _Wrap[N]):
    def hash(self) -> int:
        return self.adapter.deep_hash(self.node)

    def eq(self, other: N) -> bool:
        return self.adapter.deep_equals(self.node, other)


class _ModeStack(Generic[N]):
    stack: Final[List[bool]]

    def __init__(self, adapter: Adapter[N]):
        self.adapter: Final[Adapter[N]] = adapter
        self.stack = [False]

    @contextmanager
    def push(self, *, shallow: bool) -> Iterator[None]:
        self.stack.append(shallow)
        try:
            yield
        finally:
            popped = self.stack.pop()
            assert shallow == popped

    def children(self, node: N) -> Sequence[N]:
        return self.adapter.children(node)

    def wrap(self, node: N) -> _Wrap[N]:
        if self.stack[-1]:
            return _Shallow(self.adapter, node)
        else:
            return _Deep(self.adapter, node)

    def wrap_all(self, nodes: Sequence[N]) -> List[_Wrap[N]]:
        return [self.wrap(n) for n in nodes]


class Tag(IntEnum):
    REPLACE = auto()
    DELETE = auto()
    INSERT = auto()
    EQUAL = auto()
    DESCEND = auto()

    @staticmethod
    def from_str(tag: str) -> "Tag":
        if tag == "replace":
            return Tag.REPLACE
        elif tag == "delete":
            return Tag.DELETE
        elif tag == "insert":
            return Tag.INSERT
        elif tag == "equal":
            return Tag.EQUAL
        else:
            raise ValueError(f"unknown opcode `{tag}`")


BaseOperation = NamedTuple(
    "BaseOperation",
    (
        ("tag", Tag),
        ("i1", int),
        ("i2", int),
        ("j1", int),
        ("j2", int),
        ("sub", Optional[Sequence["Operation"]]),
    ),
)


T = TypeVar("T", bound="Operation")


class Operation(BaseOperation):
    @classmethod
    def from_sequence_matcher(
        cls: Type[T], v: Tuple[str, int, int, int, int]
    ) -> T:
        tag = Tag.from_str(v[0])
        return cls(tag=tag, i1=v[1], i2=v[2], j1=v[3], j2=v[4], sub=None)


class TreeMatcher(Generic[N]):
    """Objects of this class are able to match trees. This is similar in
    spirit to `difflib.SequenceMatcher'"""

    def __init__(self, adapter: Adapter[N], before: N, after: N):
        self._adapter: Final[_ModeStack[N]] = _ModeStack(adapter)
        self._before: Final[N] = before
        self._after: Final[N] = after
        self.is_junk = None

    def compute_operations(self) -> Sequence[Operation]:
        with self._adapter.push(shallow=True):
            sm = SequenceMatcher(
                self.is_junk,
                [
                    self._adapter.wrap(self._before),
                ],
                [
                    self._adapter.wrap(self._after),
                ],
            )
            rootOpcodes = sm.get_opcodes()
            if rootOpcodes[0][0] == "equal":
                return [
                    Operation(
                        tag=Tag.DESCEND,
                        i1=0,
                        i2=1,
                        j1=0,
                        j2=1,
                        sub=self._resolveRootEqual(self._before, self._after),
                    )
                ]
            else:
                return [
                    Operation.from_sequence_matcher(v) for v in rootOpcodes
                ]

    def _resolveRootEqual(self, aElem: N, bElem: N) -> Sequence[Operation]:
        """Considers children of `aElem` and `bElem` which have equal roots.
        Returns opcodes for the children."""
        with self._adapter.push(shallow=False):
            a_children = self._adapter.children(aElem)
            b_children = self._adapter.children(bElem)
            a = self._adapter.wrap_all(a_children)
            b = self._adapter.wrap_all(b_children)
            sm = SequenceMatcher(self.is_junk, a, b)
            nestedOpcodes = sm.get_opcodes()
            return self._resolveDeepReplace(
                nestedOpcodes, a_children, b_children
            )

    def _resolveDeepReplace(
        self,
        opcodes: Sequence[Tuple[str, int, int, int, int]],
        a: Sequence[N],
        b: Sequence[N],
    ) -> Sequence[Operation]:
        """Resolves ``replace`` elements in `opcodes` pertaining to `a` and
        `b`. Returns opcodes including nested elements for these cases."""
        result = []
        for i in range(len(opcodes)):
            (opcode, aBeg, aEnd, bBeg, bEnd) = opcodes[i]
            if opcode != "replace":
                result.append(Operation.from_sequence_matcher(opcodes[i]))
                continue
            with self._adapter.push(shallow=True):
                a_wrap = self._adapter.wrap_all(a[aBeg:aEnd])
                b_wrap = self._adapter.wrap_all(b[bBeg:bEnd])
                sm = SequenceMatcher(self.is_junk, a_wrap, b_wrap)
                rootOpcodes = sm.get_opcodes()
                for j in range(len(rootOpcodes)):
                    (
                        subOpcode,
                        aSubBeg,
                        aSubEnd,
                        bSubBeg,
                        bSubEnd,
                    ) = rootOpcodes[j]
                    if subOpcode != "equal":
                        result.append(
                            Operation(
                                tag=Tag.from_str(subOpcode),
                                i1=aBeg + aSubBeg,
                                i2=aBeg + aSubEnd,
                                j1=bBeg + bSubBeg,
                                j2=bBeg + bSubEnd,
                                sub=None,
                            )
                        )
                    else:
                        for k in range(aSubEnd - aSubBeg):
                            aIdx = aBeg + aSubBeg + k
                            bIdx = bBeg + bSubBeg + k
                            result.append(
                                Operation(
                                    tag=Tag.DESCEND,
                                    i1=aIdx,
                                    i2=aIdx + 1,
                                    j1=bIdx,
                                    j2=bIdx + 1,
                                    sub=self._resolveRootEqual(
                                        a[aIdx], b[bIdx]
                                    ),
                                )
                            )
        return result
