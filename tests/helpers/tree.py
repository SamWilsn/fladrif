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
from typing import List

from fladrif.treediff import Adapter


@dataclass
class MockNode:
    internal: int
    children: List["MockNode"] = field(default_factory=list)

    def add(self, child: "MockNode") -> "MockNode":
        self.children.append(child)
        return self


class MockAdapter(Adapter[MockNode]):
    def shallow_equals(self, lhs: MockNode, rhs: MockNode) -> bool:
        return lhs.internal == rhs.internal

    def shallow_hash(self, node: MockNode) -> int:
        return hash(node.internal)

    def children(self, node: MockNode) -> List[MockNode]:
        return node.children
