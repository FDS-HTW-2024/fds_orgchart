from dataclasses import dataclass
from collections import namedtuple

Point = namedtuple("Point", ["x", "y"], defaults=[0.0, 0.0])


@dataclass
class Rectangle:
    """Represents a Rectangle in the orgchart"""
    top_left: Point
    bottom_right: Point


@dataclass
class Line:
    p0: Point
    p1: Point


@dataclass
class TextBlock:
    """Represents a textblock inside a rectangle.
    There can be multiple textblocks in a rectangle"""
    bounding_box: Rectangle
    content: str


@dataclass
class ContentNode:
    rect: Rectangle
    content: list[TextBlock]
