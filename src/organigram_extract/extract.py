import bisect
from collections import defaultdict
from sys import float_info
from typing import Any, Callable, Generator

from pymupdf import Page, TEXTFLAGS_RAWDICT, TEXT_PRESERVE_IMAGES

from organigram_extract.data import Line, Point, Rect, TextLine, ContentNode

def extract_text(text_blocks: list[dict[str, Any]]) -> list[TextLine]:
    lines = list()

    for block in text_blocks:
        for line in block["lines"]:
            line_text = ""
            bbox = Rect()
            endswith_whitespace = False

            for span in line["spans"]:
                span_bbox = Rect()
                span_origin = Point()
    
                for char in span["chars"]:
                    if not char["c"].isspace():
                        char_bbox = char["bbox"]
                        char_origin = char["origin"]

                        if span_bbox.is_empty():
                            span_origin = Point._make(char_origin)
                            span_bbox = Rect._make(char_bbox)
                        else:
                            span_bbox = Rect(span_bbox.x0,
                                             span_bbox.y0,
                                             char_bbox[2],
                                             span_bbox.y1)

                        line_text += char["c"]
                        endswith_whitespace = False
                    elif not endswith_whitespace:
                        line_text += " "
                        endswith_whitespace = True

                if not span_bbox.is_empty():
                    font_a = span["ascender"]
                    font_d = span["descender"]
                    font_size = span["size"]
                    y1 = span_origin.y - font_size * font_d / (font_a - font_d)
                    y0 = span_bbox.y1 - font_size

                    if 0.0 < (y1 - y0) < font_size:
                        span_bbox = Rect(span_bbox.x0, y0, span_bbox.x1, y1)
                    
                    if bbox.is_empty():
                        bbox = span_bbox
                    else:
                        bbox = Rect(bbox.x0,
                                    min(bbox.y0, span_bbox.y0),
                                    span_bbox.x1,
                                    max(bbox.y1, span_bbox.y1))

            if not bbox.is_empty():
                lines.append(TextLine(bbox, line_text.strip()))

    lines.sort(key=lambda tb: (tb.bbox.y1, tb.bbox.x0, tb.text))

    for index in reversed(range(1, len(lines))):
        if (lines[index - 1].bbox.top_left == lines[index].bbox.top_left
                and lines[index - 1].text == lines[index].text):
            lines.pop(index)

    return lines

def extract_shapes(drawings: list[dict[str, Any]], tolerance: float):
    rects: list[Rect] = list()
    lines: list[Line] = list()

    # Extract rectangles and lines
    for drawing in drawings:
        for item in drawing["items"]:
            match item[0]:
                case "re":
                    rects.append(Rect._make(item[1]))
                case "l":
                    p0 = Point._make(item[1])
                    p1 = Point._make(item[2])

                    if p0 <= p1:
                        lines.append(Line(p0, p1))
                    else:
                        lines.append(Line(p1, p0))
                case _:
                    break

    # Line intersecting with line
    junction_by_line: defaultdict[int, list[tuple[int, Point]]] = defaultdict(list)

    # Find line intersections
    lines.sort(key=lambda l: (l.p0.x, l.p1.x, l.p0.y, l.p1.y))
    j_min = 0
    for i in range(0, len(lines) - 1):
        line_i = lines[i]

        x0 = line_i.p0.x - tolerance
        x1 = line_i.p1.x + tolerance
        j_max = bisect.bisect_right(lines,
                                    x1,
                                    lo=i + 1,
                                    key=lambda l: l.p0.x)
        for j in range(j_min, j_max):
            line_j = lines[j]

            intersection = line_i.intersection(line_j, tolerance)

            if intersection != None:
                junction_by_line[i].append((j, intersection))

        for line_p in lines[j_min:]:
            if line_p.p1.x < x0:
                j_min += 1
            else:
                break

    # Search for rectangles made up of 4 lines
    for (i, intersections) in junction_by_line.items():
        if len(intersections) < 2:
            continue

        line_k_intersections = defaultdict(list)

        # Look for common connected line of intersecting lines
        for (j, intersection_j) in intersections:
            for (k, intersection_k) in junction_by_line.get(j, []):
                line_k_intersections[k].append(intersection_j)
                line_k_intersections[k].append(intersection_k)

        for values in line_k_intersections.values():
            if len(values) < 4:
                continue

            x0 = float_info.max
            y0 = float_info.max
            x1 = float_info.min
            y1 = float_info.min

            for p in values:
                x0 = min(x0, p.x)
                y0 = min(y0, p.y)
                x1 = max(x1, p.x)
                y1 = max(y1, p.y)

            # TODO: Find better heuristic for tiny rectangles
            if x1 - x0 < tolerance or y1 - y0 < tolerance:
                continue

            rects.append(Rect(x0, y0, x1, y1))

            # TODO: Remove lines that make up a rectangle by setting line to None at index

    return (rects, lines, junction_by_line)

def extract(page: Page, tolerance: float = 1.0):
    (rects, lines, junction_by_line) = extract_shapes(page.get_cdrawings(), tolerance)
    text = extract_text(page.get_text("rawdict", flags=TEXTFLAGS_RAWDICT & ~TEXT_PRESERVE_IMAGES)["blocks"])
    text_block_by_rectangle: defaultdict[int, list[TextLine]] = defaultdict(list)

    rects.sort()
    for line in text:
        bbox = line.bbox
        rect_index = None
        top_left = None

        end = bisect.bisect_right(rects, bbox.top_left, key=lambda r: r.top_left)
        for (index, rectangle) in enumerate(rects[:end]):
            if (rectangle.top_left != top_left
                    and rectangle.contains(bbox.bottom_right)):
                rect_index = index
                top_left = rectangle.top_left

        if rect_index != None:
            text_block_by_rectangle[rect_index].append(line)
        else:
            print(f"[WARN]: No rectangle found for {line=}")

    content_nodes = [ContentNode(rects[index], text_block) for (index, text_block) in text_block_by_rectangle.items()]

    return (rects, lines, junction_by_line, text, content_nodes)

