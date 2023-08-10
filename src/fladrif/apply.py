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

from dataclasses import dataclass
from itertools import zip_longest
from typing import (
    Final,
    Generic,
    Iterable,
    Iterator,
    Optional,
    Sequence,
    Tuple,
)

from .treediff import Adapter, N, Operation, Tag


@dataclass
class _Level(Generic[N]):
    before: Sequence[N]
    after: Sequence[N]
    operations: Iterator[Operation]


class Apply(Generic[N]):
    def __init__(self, adapter: Adapter[N], before: N, after: N):
        self.adapter: Final[Adapter[N]] = adapter
        self.before: N = before
        self.after: N = after

    def _kids(
        self,
        op: Operation,
        stack: Sequence[_Level[N]],
    ) -> Tuple[Sequence[N], Sequence[N]]:
        return (
            stack[-1].before[op.i1 : op.i2],
            stack[-1].after[op.j1 : op.j2],
        )

    def apply(self, operations: Iterable[Operation]) -> None:
        stack = [
            _Level(
                before=[self.before],
                after=[self.after],
                operations=iter(operations),
            )
        ]

        while stack:
            level = stack[-1]
            try:
                op = next(level.operations)
            except StopIteration:
                stack.pop()

                # Trigger ascend unless it's the root pair.
                if stack:
                    self.ascend()

                continue

            before, after = self._kids(op, stack)

            match op.tag:
                case Tag.REPLACE:
                    assert op.sub is None
                    self.replace(before, after)
                case Tag.DELETE:
                    assert op.sub is None
                    assert len(after) == 0, f"op: {op}"
                    assert len(before) > 0, f"op: {op}"
                    self.delete(before)
                case Tag.INSERT:
                    assert op.sub is None
                    assert len(before) == 0, f"op: {op}"
                    assert len(after) > 0, f"op: {op}"
                    self.insert(after)
                case Tag.EQUAL:
                    assert op.sub is None
                    assert len(before) > 0, f"op: {op}"
                    assert len(after) > 0, f"op: {op}"
                    self.equal(before, after)
                case Tag.DESCEND:
                    assert 1 == len(before)
                    assert 1 == len(after)
                    assert op.sub is not None, f"op: {op}"
                    stack.append(
                        _Level(
                            before=self.adapter.children(before[0]),
                            after=self.adapter.children(after[0]),
                            operations=iter(op.sub),
                        )
                    )
                    self.descend(before[0], after[0])

    def replace(self, before: Sequence[N], after: Sequence[N]) -> None:
        pass

    def delete(self, before: Sequence[N]) -> None:
        pass

    def insert(self, after: Sequence[N]) -> None:
        pass

    def equal(self, before: Sequence[N], after: Sequence[N]) -> None:
        pass

    def descend(self, before: N, after: N) -> None:
        pass

    def ascend(self) -> None:
        pass
