from dataclasses import dataclass
from collections import namedtuple
from math import sqrt
import typing

Point = namedtuple("Point", ["x", "y"], defaults=[0.0, 0.0])


class Rectangle(typing.NamedTuple):
    """Represents a Rectangle in the orgchart"""
    top_left: Point
    bottom_right: Point

    def inflate(self, value: float):
        return Rectangle(
            top_left=Point(self.top_left.x - value, self.top_left.y - value),
            bottom_right=Point(self.bottom_right.x + value,
                               self.bottom_right.y + value)
        )


class Line(typing.NamedTuple):
    p0: Point
    p1: Point

    # Kurbo Library Source: https://github.com/linebender/kurbo/blob/884483b3de412c7c10e2fff4f43dbe96304c0dbd/src/line.rs#L44
    def intersection(self, line: "Line", tolerance: float = 0.0):
        lengthAB = sqrt(pow(self.p1.x - self.p0.x, 2) +
                        pow(self.p1.y - self.p0.y, 2))
        lengthCD = sqrt(pow(line.p1.x - line.p0.x, 2) +
                        pow(line.p1.y - line.p0.y, 2))
        newLengthAB = lengthAB + tolerance
        newLengthCD = lengthCD + tolerance

        offset_ab = Point((self.p1.x - self.p0.x) / lengthAB * newLengthAB,
                          (self.p1.y - self.p0.y) / lengthAB * newLengthAB)
        offset_cd = Point((line.p1.x - line.p0.x) / lengthCD * newLengthCD,
                          (line.p1.y - line.p0.y) / lengthCD * newLengthCD)

        a = Point(self.p1.x - offset_ab.x, self.p1.y - offset_ab.y)
        b = Point(self.p0.x + offset_ab.x, self.p0.y + offset_ab.y)
        c = Point(line.p1.x - offset_cd.x, line.p1.y - offset_cd.y)
        d = Point(line.p0.x + offset_cd.x, line.p0.y + offset_cd.y)

        ab = Point(b.x - a.x, b.y - a.y)
        cd = Point(d.x - c.x, d.y - c.y)
        ab_cross_cd = ab.x * cd.y - ab.y * cd.x

        if ab_cross_cd == 0.0:
            return None

        ca = Point(a.x - c.x, a.y - c.y)
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
    text_blocks: list[TextBlock]

    def __hash__(self):
        return hash((tuple(self.text_blocks)))
