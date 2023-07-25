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
    ) -> Iterable[Tuple[Optional[N], Optional[N]]]:
        return zip_longest(
            stack[-1].before[op.i1 : op.i2], stack[-1].after[op.j1 : op.j2]
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

            match op.tag:
                case Tag.REPLACE:
                    assert op.sub is None
                    for before, after in self._kids(op, stack):
                        if before is not None and after is not None:
                            self.replace(before, after)
                        elif before is not None:
                            self.delete(before)
                        elif after is not None:
                            self.insert(after)
                        else:
                            assert False, f"op: {op}"
                case Tag.DELETE:
                    assert op.sub is None
                    for before, after in self._kids(op, stack):
                        assert before is not None, f"op: {op}"
                        assert after is None, f"op: {op}"
                        self.delete(before)
                case Tag.INSERT:
                    assert op.sub is None
                    for before, after in self._kids(op, stack):
                        assert before is None, f"op: {op}"
                        assert after is not None, f"op: {op}"
                        self.insert(after)
                case Tag.EQUAL:
                    assert op.sub is None
                    for before, after in self._kids(op, stack):
                        assert before is not None, f"op: {op}"
                        assert after is not None, f"op: {op}"
                        self.equal(before, after)
                case Tag.DESCEND:
                    kids = list(self._kids(op, stack))
                    assert 1 == len(kids)
                    before, after = kids[0]
                    assert before is not None, f"op: {op}"
                    assert after is not None, f"op: {op}"
                    assert op.sub is not None, f"op: {op}"
                    stack.append(
                        _Level(
                            before=self.adapter.children(before),
                            after=self.adapter.children(after),
                            operations=iter(op.sub),
                        )
                    )
                    self.descend(before, after)

    def replace(self, before: N, after: N) -> None:
        pass

    def delete(self, before: N) -> None:
        pass

    def insert(self, after: N) -> None:
        pass

    def equal(self, before: N, after: N) -> None:
        pass

    def descend(self, before: N, after: N) -> None:
        pass

    def ascend(self) -> None:
        pass
