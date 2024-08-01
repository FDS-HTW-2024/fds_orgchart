from dataclasses import dataclass
from collections import namedtuple
from typing import NamedTuple, Optional, Self

class Point(NamedTuple):
    """Represents a 2D coordinate in a Drawing

    The origin of coordinates is in the top left corner, which is different
    from the PDF coordinate system.
    """

    x: float = 0.0
    y: float = 0.0

    def __add__(self, other: Self) -> Self:
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Self) -> Self:
        return Point(self.x - other.x, self.y - other.y)

def grid_distance(x: float, y: float) -> float:
    return abs(x) + abs(y)

class Rect(NamedTuple):
    """Represents a rectangle in a Drawing

    It stores the top left (x0, y0) and bottom right (x1, y1) coordinate of an
    axis-aligned box. It is used either as a bounding box for other drawing
    objects like TextSpan or as the visible box containing content.
    """

    x0: float = 0.0
    y0: float = 0.0
    x1: float = 0.0
    y1: float = 0.0

    def contains(self, other: Self) -> bool:
        return (self.x0 <= other.x0 and self.y0 <= other.y0
                and other.x1 <= self.x1 and other.y1 <= self.y1)

class Line(NamedTuple):
    """Represents a line in a Drawing

    It stores the start (p0) and end (p1) as two points. Lines are of
    importance because many older organigrams draw rectangles as four (almost)
    connected lines.
    """

    p0: Point
    p1: Point

    # Kurbo Library Source: https://github.com/linebender/kurbo/blob/884483b3de412c7c10e2fff4f43dbe96304c0dbd/src/line.rs#L44:c
    def intersection(self, line: Self, tolerance: float) -> Optional[Self]:
        a = self.p1
        b = self.p0
        c = line.p1
        d = line.p0

        ab_x = b.x - a.x
        ab_y = b.y - a.y
        cd_x = d.x - c.x
        cd_y = d.y - c.y
        ab_cross_cd = ab_x * cd_y - ab_y * cd_x

        if ab_cross_cd == 0.0:
            return None

        ca_x = a.x - c.x
        ca_y = a.y - c.y
        ab_cross_ca = ab_x * ca_y - ab_y * ca_x
        cd_cross_ca = cd_x * ca_y - cd_y * ca_x
        # h and g are the factors how much a point should be moved along the line.
        g = cd_cross_ca / ab_cross_cd
        h = ab_cross_ca / ab_cross_cd

        ab_new_x = ab_x * g
        ab_new_y = ab_y * g
        cd_new_x = cd_x * h
        cd_new_y = cd_y * h

        # The values of g and h must be between 0 and 1, otherwise 
        # check wether the offset is within tolerance.
        if ((g < 0.0 and tolerance < grid_distance(ab_new_x, ab_new_y))
                or (1.0 < g and tolerance < grid_distance(ab_new_x - ab_x, ab_new_y - ab_y))
                or (h < 0.0 and tolerance < grid_distance(cd_new_x, cd_new_y))
                or (1.0 < h and tolerance < grid_distance(cd_new_x - cd_x, cd_new_y - cd_y))):
            return None

        return Point(c.x + cd_new_x, c.y + cd_new_y)

class TextSpan(NamedTuple):
    """Represents a text span in a Drawing

    In many cases a TextSpan should represent a text line or even a text
    block. However, PDF does not preserve the intent and just the draw
    command, which means the bounding box is necessary to compute the words
    when characters are separately stored.
    """

    bbox: Rect
    text: str

class Drawing(NamedTuple):
    """Represents a file containing a drawing like an organigram

    The purpose of this data type is to abstract over file formats like PDF,
    which allows to integrate other data sources easily. In PDF terms it is
    a single page.
    """

    width: float
    height: float
    rects: list[Rect]
    lines: list[Line]
    text_spans: list[TextSpan]
