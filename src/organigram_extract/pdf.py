from typing import Iterator

import pymupdf
from pymupdf import Page, TEXTFLAGS_RAWDICT, TEXT_PRESERVE_IMAGES

from organigram_extract.data import Drawing, Line, Point, Rect, TextSpan

def open(path: str) -> Iterator[Drawing]:
    pdf = pymupdf.open(path)

    for page in pdf:
        yield extract_drawing(page)

def extract_drawing(page: Page) -> Drawing:
    def generate_text_spans(blocks):
        for block in blocks:
            for line in block["lines"]:
                for span in line["spans"]:
                    span_text = ""
                    span_bbox = None
                    span_origin = None
                    has_whitespace = False

                    for char in span["chars"]:
                        c = char["c"]
                        if c.isprintable() and not c.isspace():
                            char_bbox = char["bbox"]
                            char_origin = char["origin"]

                            if span_bbox == None:
                                span_origin = Point._make(char_origin)
                                span_bbox = Rect._make(char_bbox)
                            else:
                                span_bbox = Rect(span_bbox.x0, span_bbox.y0,
                                                 char_bbox[2], span_bbox.y1)

                            span_text += c
                            has_whitespace = False
                        elif not has_whitespace:
                            span_text += " "
                            has_whitespace = True

                    if span_bbox != None:
                        font_a = span["ascender"]
                        font_d = span["descender"]
                        font_size = span["size"]
                        y1 = span_origin.y - font_size * font_d / (font_a - font_d)
                        y0 = span_bbox.y1 - font_size

                        if 0.0 < (y1 - y0) < font_size:
                            span_bbox = Rect(span_bbox.x0, y0,
                                             span_bbox.x1, y1)

                        yield TextSpan(span_bbox, span_text.strip())

    page.remove_rotation()
    
    rects = list()
    lines = list()

    # Extract rectangles and lines
    drawings = page.get_cdrawings()
    for drawing in drawings:
        line_count = 0

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
                    line_count += 1
                case _:
                    del lines[len(lines) - line_count:]
                    break

    raw_text = page.get_text("rawdict", flags=TEXTFLAGS_RAWDICT & ~TEXT_PRESERVE_IMAGES)
    text_spans = list(generate_text_spans(raw_text["blocks"]))

    return Drawing(page.rect.width, page.rect.height,
                   rects, lines, text_spans)
