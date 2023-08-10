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

from dataclasses import dataclass, field
from typing import Final, Iterable, List, Sequence, TypeAlias, Union

from helpers.tree import MockAdapter
from helpers.tree import MockNode as N

from fladrif import apply
from fladrif.treediff import Operation as Op
from fladrif.treediff import TreeMatcher


@dataclass
class DiffNode:
    before: Sequence[N]
    after: Sequence[N]


@dataclass
class SameNode:
    internal: int
    children: List["AppliedNode"] = field(default_factory=list)

    def add(self, child: "AppliedNode") -> "SameNode":
        self.children.append(child)
        return self


AppliedNode: TypeAlias = Union[DiffNode, SameNode, N]


class Apply(apply.Apply[N]):
    stack: Final[List[AppliedNode]]
    root: SameNode

    def __init__(self, before: N, after: N) -> None:
        super().__init__(MockAdapter(), before, after)
        self.stack = []
        self.root = SameNode(-1)

    def apply(self, operations: Iterable[Op]) -> None:
        assert not self.stack
        self.root.children.clear()

        try:
            self.stack.append(self.root)
            super().apply(operations)
        finally:
            self.stack.clear()

    def replace(self, before: Sequence[N], after: Sequence[N]) -> None:
        parent = self.stack[-1]
        assert isinstance(parent, SameNode)
        parent.add(DiffNode(before=before, after=after))

    def delete(self, before: Sequence[N]) -> None:
        parent = self.stack[-1]
        assert isinstance(parent, SameNode)
        parent.add(DiffNode(before=before, after=tuple()))

    def insert(self, after: Sequence[N]) -> None:
        parent = self.stack[-1]
        assert isinstance(parent, SameNode)
        parent.add(DiffNode(before=tuple(), after=after))

    def equal(self, before: Sequence[N], after: Sequence[N]) -> None:
        parent = self.stack[-1]
        assert isinstance(parent, SameNode)
        for x in after:
            parent.add(x)

    def descend(self, before: N, after: N) -> None:
        parent = self.stack[-1]
        assert isinstance(parent, SameNode)
        node = SameNode(after.internal)
        parent.add(node)
        self.stack.append(node)

    def ascend(self) -> None:
        self.stack.pop()

    def output(self) -> AppliedNode:
        assert 1 == len(self.root.children)
        return self.root.children[0]


def test_single_node_same() -> None:
    before = N(1)
    adapter = MockAdapter()
    matcher = TreeMatcher(adapter, before, before)
    operations = matcher.compute_operations()

    applier = Apply(before, before)
    applier.apply(operations)

    actual = applier.output()
    assert isinstance(actual, (SameNode, N))
    assert 1 == actual.internal
    assert not actual.children


def test_single_node_equal() -> None:
    before = N(1)
    after = N(1)
    adapter = MockAdapter()
    matcher = TreeMatcher(adapter, before, after)
    operations = matcher.compute_operations()

    applier = Apply(before, before)
    applier.apply(operations)

    actual = applier.output()
    assert isinstance(actual, (SameNode, N))
    assert 1 == actual.internal
    assert not actual.children


def test_single_node_different() -> None:
    before = N(1)
    after = N(2)
    adapter = MockAdapter()
    matcher = TreeMatcher(adapter, before, after)
    operations = matcher.compute_operations()

    applier = Apply(before, after)
    applier.apply(operations)

    actual = applier.output()
    assert isinstance(actual, DiffNode)

    assert len(actual.before) == 1
    assert isinstance(actual.before[0], (SameNode, N))
    assert actual.before[0].internal == 1
    assert not actual.before[0].children

    assert len(actual.after) == 1
    assert isinstance(actual.after[0], (SameNode, N))
    assert actual.after[0].internal == 2
    assert not actual.after[0].children


def test_one_child_node_equal() -> None:
    before = N(1).add(N(2))
    after = N(1).add(N(2))
    adapter = MockAdapter()
    matcher = TreeMatcher(adapter, before, after)
    operations = matcher.compute_operations()

    applier = Apply(before, after)
    applier.apply(operations)

    actual = applier.output()
    assert isinstance(actual, (SameNode, N))
    assert 1 == actual.internal
    assert 1 == len(actual.children)

    child = actual.children[0]
    assert isinstance(child, (SameNode, N))
    assert 2 == child.internal
    assert 0 == len(child.children)


def test_one_child_node_different_root() -> None:
    before = N(1).add(N(2))
    after = N(3).add(N(2))
    adapter = MockAdapter()
    matcher = TreeMatcher(adapter, before, after)
    operations = matcher.compute_operations()

    applier = Apply(before, after)
    applier.apply(operations)

    actual = applier.output()
    assert isinstance(actual, DiffNode)

    assert len(actual.before) == 1
    assert isinstance(actual.before[0], (SameNode, N))
    assert actual.before[0].internal == 1
    assert 1 == len(actual.before[0].children)

    child = actual.before[0].children[0]
    assert isinstance(child, (SameNode, N))
    assert 2 == child.internal
    assert 0 == len(child.children)

    assert len(actual.after) == 1
    assert isinstance(actual.after[0], (SameNode, N))
    assert actual.after[0].internal == 3
    assert 1 == len(actual.after[0].children)

    child = actual.after[0].children[0]
    assert isinstance(child, (SameNode, N))
    assert 2 == child.internal
    assert 0 == len(child.children)


def test_one_child_node_different_child() -> None:
    before = N(1).add(N(2))
    after = N(1).add(N(3))
    adapter = MockAdapter()
    matcher = TreeMatcher(adapter, before, after)
    operations = matcher.compute_operations()

    applier = Apply(before, after)
    applier.apply(operations)

    actual = applier.output()
    assert isinstance(actual, (SameNode, N))
    assert actual.internal == 1
    assert 1 == len(actual.children)

    child = actual.children[0]
    assert isinstance(child, DiffNode)

    assert len(child.before) == 1
    assert isinstance(child.before[0], (SameNode, N))
    assert child.before[0].internal == 2
    assert not child.before[0].children

    assert len(child.after) == 1
    assert isinstance(child.after[0], (SameNode, N))
    assert child.after[0].internal == 3
    assert not child.after[0].children


def test_structure() -> None:
    before = N(1).add(N(2).add(N(3)))
    after = N(1).add(N(2)).add(N(3))
    adapter = MockAdapter()
    matcher = TreeMatcher(adapter, before, after)
    operations = matcher.compute_operations()

    applier = Apply(before, after)
    applier.apply(operations)

    actual = applier.output()
    assert isinstance(actual, (SameNode, N))
    assert actual.internal == 1
    assert 2 == len(actual.children)

    child = actual.children[0]
    assert isinstance(child, (SameNode, N))
    assert child.internal == 2
    assert 1 == len(child.children)

    grandchild = child.children[0]
    assert isinstance(grandchild, DiffNode)
    assert len(grandchild.after) == 0
    assert len(grandchild.before) == 1
    assert isinstance(grandchild.before[0], (SameNode, N))
    assert 3 == grandchild.before[0].internal
    assert 0 == len(grandchild.before[0].children)

    child = actual.children[1]
    assert isinstance(child, DiffNode)
    assert len(child.before) == 0
    assert len(child.after) == 1
    assert isinstance(child.after[0], (SameNode, N))
    assert 3 == child.after[0].internal
    assert not child.after[0].children
