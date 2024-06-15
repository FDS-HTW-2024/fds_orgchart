import itertools
from typing import Callable, Generator

import pymupdf
    
from data import Line, Point, Rectangle, TextBlock

def sorted_array_group_by[T, K](
    array: list[T],
    extract_key: Callable[[T], K] = lambda element: element
) -> Generator[tuple[K, list[T]], None, None]:
    count = len(array)

    if count == 0:
        return

    start = 0
    end = 1
    key_start = extract_key(array[0])

    while end < count:
        key_end = extract_key(array[end])

        if key_start != key_end:
            yield (key_start, array[start:end])
            start = end
            key_start = key_end

        end += 1

    if start < end:
        yield (key_start, array[start:end])

def sorted_array_find_range[T](
    array: list[T],
    predicate: Callable[[T], bool] = lambda _: False
) -> list[T]:
    start = 0
    count = len(array)

    while start < count and not predicate(array[start]):
        start += 1
    
    end = start + 1

    while end < count and predicate(array[end]):
        end += 1

    return array[start:end]

tolerance = 0.0
page = pymupdf.open("example_orgcharts/org_kultur.pdf")[0]

rectangles: list[Rectangle] = list()
lines: list[Line] = list()

for drawing in page.get_drawings():
    for item in drawing["items"]:
        match item[0]:
            case "re":
                rectangles.append(Rectangle(
                    top_left=Point._make(item[1].top_left),
                    bottom_right=Point._make(item[1].bottom_right)                 
                ))
            case "l":
                lines.append(Line(
                    p0=Point._make(item[1]),
                    p1=Point._make(item[2])                 
                ))
            case _:
                pass

# Line intersecting with line
junctions: list[tuple[int, int, Point]] = list()
# Line intersecting with rectangle
nodes = list()

lines.sort()
for l_i in range(0, len(lines)):
    line_i = lines[l_i]

    for l_j in range(l_i + 1, len(lines)):
        line_j = lines[l_j]

        intersection = line_i.intersection(line_j, tolerance)

        if intersection != None:
            junctions.append((l_i, l_j, intersection))

# Search for rectangles made up of 4 lines
j_i = 0
for (l_i, intersections) in sorted_array_group_by(junctions, lambda j: j[0]):
    intersection_count = len(intersections)
    j_i += intersection_count

    if intersection_count < 2:
        continue

    line_i = lines[l_i]

    for (_, l_j, intersection) in intersections:
        if (line_i.p0 - intersection).distance() <= tolerance:
            for (_, l_k0, _) in sorted_array_find_range(junctions[j_i:], lambda j: j[0] == l_j):
                print(l_i, l_j, l_k0)
        if (line_i.p1 - intersection).distance() <= tolerance:
            for (_, l_k1, _) in sorted_array_find_range(junctions[j_i:], lambda j: j[0] == l_j):
                print(l_i, l_j, l_k0)

