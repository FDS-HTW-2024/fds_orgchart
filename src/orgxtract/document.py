import bisect
from collections import defaultdict
import logging
from sys import float_info
from typing import Self, NamedTuple

from orgxtract.drawing import Drawing, Line, Point, Rect, TextSpan

logger = logging.getLogger(__package__)

class Document(NamedTuple):
    # The cleaned and de-duplicated data from Drawing.
    width: float
    height: float
    rects: list[Rect]
    lines: list[Line]
    text_spans: list[TextSpan]

    # The decision to store indices instead of references is more of a
    # personal preference for simple object graphs/lifetimes.

    # Rect -> list[TextSpan]
    text_blocks: dict[int, list[int]]
    # Rect -> str
    text_contents: dict[int, str]

    @staticmethod
    def extract(drawing: Drawing) -> Self:
        drawing.lines.sort(key=lambda l: (l.p0.x, l.p1.x, l.p0.y, l.p1.y))
        dedup(drawing.lines)

        # TODO: Calculate graph edges for edges
        _junctions = extract_nodes(drawing.rects, drawing.lines)

        drawing.rects.append(Rect(0.0, 0.0, drawing.width, drawing.height))
        drawing.rects.sort()
        dedup(drawing.rects)

        drawing.text_spans.sort(key=lambda ts: (ts.bbox.y0, ts.bbox.x0, ts.bbox.y1, ts.bbox.x1))
        dedup(drawing.text_spans)

        text_blocks = extract_text_blocks(drawing.rects, drawing.text_spans)

        # TODO: The page rect has to be clustered in coarse regions, otherwise
        # text lines are made up of words that are far away from each other.

        text_contents = {k:"".join(generate_text(drawing.text_spans, v))
                        for (k, v) in text_blocks.items()}

        return Document(drawing.width, drawing.height,
                        drawing.rects, drawing.lines, drawing.text_spans,
                        text_blocks, text_contents)

def extract_nodes(
        rects: list[Rect],
        lines: list[Line],
        tolerance: float = 1.0) -> dict[int, list[tuple[int, Point]]]:
    junction_by_line: defaultdict[int, list[tuple[int, Point]]] = defaultdict(list)
    j_min = 0

    # Find line intersections
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
            if x1 - x0 <= tolerance or y1 - y0 <= tolerance:
                continue

            rects.append(Rect(x0, y0, x1, y1))

            # TODO: Remove lines that make up a rectangle by setting line to None at index

    return junction_by_line

def extract_text_blocks(
        rects: list[Rect],
        text_spans: list[TextSpan]) -> dict[int | None, list[int]]:
    text_block_by_rect: defaultdict[int | None, list[int]] = defaultdict(list)

    # Sort text spans into detected rectangles.
    for s in range(0, len(text_spans)):
        (bbox, _) = text_spans[s]
        rect = None
        end = bisect.bisect_right(rects, (bbox.x0, bbox.y0), key=lambda r: (r.x0, r.y0))

        for r in reversed(range(0, end)):
            if rects[r].contains(bbox):
                rect = r
                break

        if rect != None:
            text_block_by_rect[rect].append(s)
        else:
            logger.warn("%s outside document found", text_spans[s])

    # Sort text spans in reading order.
    for text_block in text_block_by_rect.values():
        for j in range(1, len(text_block)):
            i = j - 1
            (bbox_i, _) = text_spans[text_block[i]]
            (bbox_j, _) = text_spans[text_block[j]]
            y0_max = max(bbox_i.y0, bbox_j.y0)
            y1_min = min(bbox_i.y1, bbox_j.y1)

            # Spans are within the same visual line.
            if y0_max < y1_min:
                # A swap is necessary because sometimes spans are higher
                # than their siblings.
                if bbox_j.x0 < bbox_i.x0:
                    text_block[i], text_block[j] = text_block[j], text_block[i]

    return text_block_by_rect

def generate_text(text_spans: list[TextSpan], text_block: list[int]):
    yield text_spans[text_block[0]].text

    for j in range(1, len(text_block)):
        i = j - 1
        (bbox_i, _) = text_spans[text_block[i]]
        (bbox_j, text) = text_spans[text_block[j]]
        y0_max = max(bbox_i.y0, bbox_j.y0)
        y1_min = min(bbox_i.y1, bbox_j.y1)

        # Spans are within the same visual line.
        if y0_max < y1_min:
            distance = bbox_j.x1 - bbox_i.x0

            if 0.5 <= distance:
                yield " "
        else:
            error = 0.9
            space = bbox_j.y0 - bbox_i.y1
            height = min(bbox_i.y1 - bbox_i.y0, bbox_j.y1 - bbox_j.y0) * error

            if height <= space:
                yield "\n\n"
            else:
                yield "\n"

        yield text

def dedup[T](items: list[T]):
    for i in reversed(range(1, len(items))):
        item_j = items[i]
        item_i = items[i - 1]

        if item_i == item_j:
            items.pop(i)
