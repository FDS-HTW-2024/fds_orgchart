from dataclasses import dataclass
from collections import namedtuple
from math import sqrt
from typing import NamedTuple, Self

class Point(NamedTuple):
    x: float = 0.0
    y: float = 0.0

    def __add__(self, other: Self) -> Self:
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Self) -> Self:
        return Point(self.x - other.x, self.y - other.y)
    
    def distance(self) -> float:
        return sqrt(self.x * self.x + self.y * self.y)

class Rectangle(NamedTuple):
    """Represents a Rectangle in the orgchart"""
    top_left: Point
    bottom_right: Point

    def inflate(self, value: float) -> Self:
        return Rectangle(
            top_left=Point(self.top_left.x - value, self.top_left.y - value),
            bottom_right=Point(self.bottom_right.x + value,
                               self.bottom_right.y + value)
        )


class Line(NamedTuple):
    p0: Point
    p1: Point

    # Kurbo Library Source: https://github.com/linebender/kurbo/blob/884483b3de412c7c10e2fff4f43dbe96304c0dbd/src/line.rs#L44
    def intersection(self, line: Self, tolerance: float = 0.0) -> Self:
        ab = self.p1 - self.p0
        cd = line.p1 - line.p0
        lengthAB = ab.distance()
        lengthCD = cd.distance()
        newLengthAB = lengthAB + tolerance
        newLengthCD = lengthCD + tolerance

        offset_ab = Point(ab.x / lengthAB * newLengthAB, ab.y / lengthAB * newLengthAB)
        offset_cd = Point(cd.x / lengthCD * newLengthCD, cd.y / lengthCD * newLengthCD)

        a = self.p1 - offset_ab
        b = self.p0 + offset_ab
        c = line.p1 - offset_cd
        d = line.p0 + offset_cd

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

        # The values of g and h must be between 0 and 1, otherwise the point will
        # be outside the lines.
        if 0.0 <= g <= 1.0 and 0.0 <= h <= 1.0:
            return Point(c.x + cd.x * h, c.y + cd.y * h)

        return None


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
        return hash((tuple(self.content)))
