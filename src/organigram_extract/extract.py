import bisect
from collections import defaultdict
from sys import float_info
from typing import Any

from pymupdf import Page, TEXTFLAGS_RAWDICT, TEXT_PRESERVE_IMAGES

from organigram_extract.data import Line, Point, Rect, TextLine, ContentNode

def extract_text(text_blocks: list[dict[str, Any]]):
    for block in text_blocks:
        for line in block["lines"]:
            line_text = ""
            bbox = None
            endswith_whitespace = False

            for span in line["spans"]:
                span_bbox = None
                span_origin = None
    
                for char in span["chars"]:
                    if not char["c"].isspace():
                        char_bbox = char["bbox"]
                        char_origin = char["origin"]

                        if span_bbox == None:
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

                if span_bbox != None:
                    font_a = span["ascender"]
                    font_d = span["descender"]
                    font_size = span["size"]
                    y1 = span_origin.y - font_size * font_d / (font_a - font_d)
                    y0 = span_bbox.y1 - font_size

                    if 0.0 < (y1 - y0) < font_size:
                        span_bbox = Rect(span_bbox.x0, y0, span_bbox.x1, y1)
                    
                    if bbox == None:
                        bbox = span_bbox
                    else:
                        bbox = Rect(bbox.x0,
                                    min(bbox.y0, span_bbox.y0),
                                    span_bbox.x1,
                                    max(bbox.y1, span_bbox.y1))

            if bbox != None:
                yield TextLine(bbox, line_text.strip())

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
            if x1 - x0 <= tolerance or y1 - y0 <= tolerance:
                continue

            rects.append(Rect(x0, y0, x1, y1))

            # TODO: Remove lines that make up a rectangle by setting line to None at index

    return (rects, lines, junction_by_line)

def dedup[T](items: list[T]):
    for i in reversed(range(1, len(items))):
        item_j = items[i]
        item_i = items[i - 1]

        if item_i == item_j:
            items.pop(i)

def extract(page: Page, tolerance: float = 1.0):
    (rects, lines, junction_by_line) = extract_shapes(page.get_cdrawings(), abs(tolerance))
    text = extract_text(page.get_text("rawdict", flags=TEXTFLAGS_RAWDICT & ~TEXT_PRESERVE_IMAGES)["blocks"])
    text_block_by_rect: defaultdict[Rect, list[TextLine]] = defaultdict(list)
    text_block_meta = list()

    # Sort text spans into detected rectangles.
    rects.sort()
    dedup(rects)

    for line in text:
        bbox = line.bbox
        rect = None
        end = bisect.bisect_right(rects, (bbox.x0, bbox.y0), key=lambda r: (r.x0, r.y0))

        for rectangle in reversed(rects[:end]):
            if rectangle.contains(bbox):
                rect = rectangle
                break

        if rect != None:
            text_block_by_rect[rect].append(line)
        else:
            text_block_meta.append(line)

    content_nodes = list()

    # Sort text spans in reading order and merge consecutive spans.
    for (rect, text_block) in text_block_by_rect.items():
        text_block.sort(key=lambda tb: (tb.bbox.y0, tb.bbox.x0, tb.bbox.y1, tb.bbox.x1))
        dedup(text_block)
        j = len(text_block) - 1

        while 0 < j:
            i = j - 1
            line_i = text_block[i]
            line_j = text_block[j]
            y0_max = max(line_i.bbox.y0, line_j.bbox.y0)
            y1_min = min(line_i.bbox.y1, line_j.bbox.y1)

            # Spans are within the same visual line.
            if y0_max < y1_min:
                # A merge is necessary because some spans must be encoded in a
                # a fallback font (e.g. italic '-').
                if (abs(line_i.bbox.x1 - line_j.bbox.x0) < 0.5
                        and abs(line_i.bbox.y1 - line_j.bbox.y1) < 0.5):
                    text_block[i] = TextLine(Rect(line_i.bbox.x0,
                                                  min(line_i.bbox.y0, line_j.bbox.y0),
                                                  line_j.bbox.x1,
                                                  max(line_i.bbox.y1, line_j.bbox.y1)),
                                             line_i.text + line_j.text)
                    text_block.pop(j)
                    j += 1
                else:
                    # A swap is necessary because sometimes spans are higher
                    # than their siblings.
                    if line_j.bbox.x0 < line_i.bbox.x0:
                        text_block[i], text_block[j] = text_block[j], text_block[i]

            j -= 1

        content_nodes.append(ContentNode(rect, text_block))

    return (rects, lines, junction_by_line, text_block_meta, content_nodes)

