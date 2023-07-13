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

from helpers.tree import MockAdapter
from helpers.tree import MockNode as N

from fladrif.treediff import Operation as Op
from fladrif.treediff import Tag, TreeMatcher


def test_single_node_same() -> None:
    before = N(1)
    adapter = MockAdapter()
    matcher = TreeMatcher(adapter, before, before)
    actual = matcher.compute_operations()

    assert actual == [Op(Tag.DESCEND, 0, 1, 0, 1, sub=[])]


def test_single_node_equal() -> None:
    before = N(1)
    after = N(1)
    adapter = MockAdapter()
    matcher = TreeMatcher(adapter, before, after)
    actual = matcher.compute_operations()

    assert actual == [Op(Tag.DESCEND, 0, 1, 0, 1, sub=[])]


def test_single_node_different() -> None:
    before = N(1)
    after = N(2)
    adapter = MockAdapter()
    matcher = TreeMatcher(adapter, before, after)
    actual = matcher.compute_operations()

    assert actual == [Op(Tag.REPLACE, 0, 1, 0, 1, sub=None)]


def test_one_child_node_same() -> None:
    before = N(1).add(N(2))
    adapter = MockAdapter()
    matcher = TreeMatcher(adapter, before, before)
    actual = matcher.compute_operations()

    assert actual == [
        Op(
            Tag.DESCEND,
            0,
            1,
            0,
            1,
            sub=[
                Op(Tag.EQUAL, 0, 1, 0, 1, sub=None),
            ],
        )
    ]


def test_one_child_node_equal() -> None:
    before = N(1).add(N(2))
    after = N(1).add(N(2))
    adapter = MockAdapter()
    matcher = TreeMatcher(adapter, before, after)
    actual = matcher.compute_operations()

    assert actual == [
        Op(
            Tag.DESCEND,
            0,
            1,
            0,
            1,
            sub=[
                Op(Tag.EQUAL, 0, 1, 0, 1, sub=None),
            ],
        )
    ]


def test_one_child_node_different_root() -> None:
    before = N(1).add(N(2))
    after = N(3).add(N(2))
    adapter = MockAdapter()
    matcher = TreeMatcher(adapter, before, after)
    actual = matcher.compute_operations()

    assert actual == [Op(Tag.REPLACE, 0, 1, 0, 1, sub=None)]


def test_one_child_node_different_child() -> None:
    before = N(1).add(N(2))
    after = N(1).add(N(3))
    adapter = MockAdapter()
    matcher = TreeMatcher(adapter, before, after)
    actual = matcher.compute_operations()

    assert actual == [
        Op(
            Tag.DESCEND,
            0,
            1,
            0,
            1,
            sub=[
                Op(Tag.REPLACE, 0, 1, 0, 1, sub=None),
            ],
        )
    ]


def test_structure() -> None:
    before = N(1).add(N(2).add(N(3)))
    after = N(1).add(N(2)).add(N(3))
    adapter = MockAdapter()
    matcher = TreeMatcher(adapter, before, after)
    actual = matcher.compute_operations()

    assert actual == [
        Op(
            Tag.DESCEND,
            0,
            1,
            0,
            1,
            sub=[
                Op(
                    Tag.DESCEND,
                    0,
                    1,
                    0,
                    1,
                    sub=[
                        Op(Tag.DELETE, 0, 1, 0, 0, sub=None),
                    ],
                ),
                Op(Tag.INSERT, 1, 1, 1, 2, sub=None),
            ],
        )
    ]
