from typing import Callable, Generator

import pymupdf
    
from data import Line, Point, Rectangle, TextBlock, ContentNode

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

def extract(input: str, tolerance: float = 1.0):
    page = pymupdf.open(input)[0]

    rectangles: list[Rectangle] = list()
    lines: list[Line] = list()

    # Extract rectangles and lines
    for drawing in page.get_drawings():
        for item in drawing["items"]:
            match item[0]:
                case "re":
                    rectangles.append(Rectangle(
                        top_left=Point._make(item[1].top_left),
                        bottom_right=Point._make(item[1].bottom_right)                 
                    ))
                case "l":
                    p0 = Point._make(item[1])
                    p1 = Point._make(item[2])

                    if p0 <= p1:
                        lines.append(Line(p0=p0, p1=p1))
                    else:
                        lines.append(Line(p0=p1, p1=p0))
                case _:
                    pass

    # Line intersecting with line
    junctions: list[tuple[int, int, Point]] = list()

    # Find line intersections
    lines.sort()
    for l_i in range(0, len(lines)):
        line_i = lines[l_i]

        for l_j in range(0, len(lines)):
            line_j = lines[l_j]

            intersection = line_i.intersection(line_j, tolerance)

            if intersection != None:
                junctions.append((l_i, l_j, intersection))

    # Search for rectangles made up of 4 lines
    for (l_i, intersections) in sorted_array_group_by(junctions, lambda j: j[0]):
        intersection_count = len(intersections)

        if intersection_count < 2:
            continue

        line_i = lines[l_i]
        line_k0_intersections = dict()
        line_k1_intersections = dict()

        # Look for common connected line of intersecting lines
        # TODO: Check that the it is not a triangle
        for (_, l_j, intersection_j) in intersections:
            if (line_i.p0 - intersection_j).distance() <= tolerance:
                for (_, l_k0, intersection_k0) in sorted_array_find_range(junctions, lambda j: j[0] == l_j):
                    line_k0_intersections.setdefault(l_k0, list()).append((intersection_j, intersection_k0))
            elif (line_i.p1 - intersection_j).distance() <= tolerance:
                for (_, l_k1, intersection_k1) in sorted_array_find_range(junctions, lambda j: j[0] == l_j):
                    line_k1_intersections.setdefault(l_k1, list()).append((intersection_j, intersection_k1))

        for (line_index, values0) in line_k0_intersections.items():
            values1 = line_k1_intersections.get(line_index, None)

            if values1 == None:
                continue

            for ((p0, p1), (p2, p3)) in zip(values0, values1):
                points = [p0, p1, p2, p3]
                points.sort()
                top_left = points[0]
                bottom_right=points[3]

                (width, height) = bottom_right - top_left

                # FIXME: Floating number 0 check is done by doing less than EPSILON
                if width == 0.0 or height == 0.0:
                    continue
            
                rectangles.append(Rectangle(
                    top_left=top_left,
                    bottom_right=bottom_right
                ))

            # TODO: Remove lines that make up a rectangle by setting line to None at index


    words = page.get_text("blocks", sort=True)  # list of words on page
    content_nodes = list()

    for rect in rectangles:
        rect_words = [w for w in words if pymupdf.Rect(
            w[:4]).intersects(rect)]
        text_blocks = list()
        for (x0, y0, x1, y1, word, _, _) in rect_words:
            text_block = TextBlock(bounding_box=Rectangle(
                Point(x0, y0), Point(x1, y1)), content=word)
            text_blocks.append(text_block)
        content_node = ContentNode(rect=rect, content=text_blocks)
        content_nodes.append(content_node)

    return (rectangles, lines, junctions, words, content_nodes)
