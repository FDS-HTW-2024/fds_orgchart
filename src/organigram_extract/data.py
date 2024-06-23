from dataclasses import dataclass
from collections import namedtuple
from math import sqrt
from typing import NamedTuple, Optional, Self

class Point(NamedTuple):
    x: float = 0.0
    y: float = 0.0

    def __add__(self, other: Self) -> Self:
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Self) -> Self:
        return Point(self.x - other.x, self.y - other.y)
    
    def distance(self) -> float:
        return sqrt(self.x * self.x + self.y * self.y)
    
    def grid_distance(self) -> float:
        return abs(self.x) + abs(self.y)

class Rectangle(NamedTuple):
    """Represents a Rectangle in the orgchart"""
    top_left: Point
    bottom_right: Point

    def inflate(self, value: float) -> Self:
        offset = Point(value, value)
        return Rectangle(
            top_left=self.top_left - offset,
            bottom_right=self.bottom_right.x + offset
        )

    def contains(self, point: Point) -> bool:
        return (self.top_left.x <= point.x <= self.bottom_right.x
                and self.top_left.y <= point.y <= self.bottom_right.y)


class Line(NamedTuple):
    p0: Point
    p1: Point

    # Kurbo Library Source: https://github.com/linebender/kurbo/blob/884483b3de412c7c10e2fff4f43dbe96304c0dbd/src/line.rs#L44
    def intersection(self, line: Self, tolerance: float = 0.0) -> Optional[Self]:
        a = self.p1
        b = self.p0
        c = line.p1
        d = line.p0

        ab = b - a
        cd = d - c
        ab_cross_cd = ab.x * cd.y - ab.y * cd.x

        if ab_cross_cd == 0.0:
            return None

        ca = a - c
        ab_cross_ca = ab.x * ca.y - ab.y * ca.x
        cd_cross_ca = cd.x * ca.y - cd.y * ca.x
        # h and g are the factors how much a point should be moved along the line.
        g = cd_cross_ca / ab_cross_cd
        h = ab_cross_ca / ab_cross_cd

        ab_new = Point(ab.x * g, ab.y * g)
        cd_new = Point(cd.x * h, cd.y * h)

        # The values of g and h must be between 0 and 1, otherwise 
        # check wether the offset is within tolerance.
        if ((g < 0.0 and tolerance < ab_new.grid_distance())
                or (1.0 < g and tolerance < (ab_new - ab).grid_distance())
                or (h < 0.0 and tolerance < cd_new.grid_distance())
                or (1.0 < h and tolerance < (cd_new - cd).grid_distance())):
            return None

        return c + cd_new


@dataclass
class TextBlock:
    """Represents a textblock inside a rectangle.
    There can be multiple textblocks in a rectangle"""
    bounding_box: Rectangle
    content: str

    def __hash__(self):
        return hash((self.bounding_box, self.content))


@dataclass
class ContentNode:
    rect: Rectangle
    content: list[TextBlock]

    def __hash__(self):
        return hash((tuple(self.text_blocks)))
