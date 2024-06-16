import fitz
from data import Point, Line, Rectangle, TextBlock, ContentNode


def make_text(words):
    """Return textstring output of get_text("words").
    Word items are sorted for reading sequence left to right,

    top to bottom.
    """
    line_dict = {}  # key: vertical coordinate, value: list of words
    words.sort(key=lambda w: w[0])  # sort by horizontal coordinate
    for w in words:  # fill the sorted_rect_words dictionary
        y1 = round(w[3], 1)  # bottom of a word: don't be too picky!
        word = w[4]  # the text of the word
        # read current sorted_rect_words content
        sorted_rect_words = line_dict.get(y1, [])
        sorted_rect_words.append(word)  # append new word
        line_dict[y1] = sorted_rect_words  # write back to dict
    lines = list(line_dict.items())
    lines.sort()  # sort vertically
    return "\n".join([" ".join(sorted_rect_words[1]) for sorted_rect_words in lines])


doc = fitz.open("example_orgcharts/org_kultur.pdf")
page = doc[0]  # we want text from this page

drawings_list = page.get_drawings()
rects: list[Rectangle] = list()
words = page.get_text("blocks", sort=True)  # list of words on page
lines: list[Line] = list()

for d in drawings_list:
    for item in d["items"]:
        match item[0]:
            case "re":
                rects.append(
                    Rectangle(top_left=item[1].top_left, bottom_right=item[1].bottom_right))
            case "l":
                lines.append(
                    Line(p0=Point._make(item[1]), p1=Point._make(item[2])))
            case _:
                pass

# create ContentNodes
for rect in rects:
    rect_words = [w for w in words if fitz.Rect(
        w[:4]).intersects(rect)]
    text_blocks = list()
    for (x0, y0, x1, y1, word, _, _) in rect_words:
        text_block = TextBlock(bounding_box=Rectangle(
            Point(x0, y0), Point(x1, y1)), content=word)
        text_blocks.append(text_block)
    content_node = ContentNode(rect=rect, content=text_blocks)
    print(content_node)
    print("################")

outpdf = fitz.open()
outpage = outpdf.new_page(width=page.rect.width, height=page.rect.height)
shape = outpage.new_shape()


def is_node_point(rect: Rectangle, point: Point, threshold=1.0):
    return fitz.Rect(rect.inflate(threshold)).contains(point)


node_points = []
graph_lines = []

for rect in rects:
    shape.draw_rect(rect)
    for line in lines:
        if is_node_point(rect, line.p0):
            print("intersects")
            shape.draw_circle(line.p0, 4)
            node_points.append(line.p0)
        if is_node_point(rect, line.p1):
            print("intersects")
            shape.draw_circle(line.p1, 4)
            node_points.append(line.p1)
        if (not is_node_point(rect, line.p0) and
                not is_node_point(rect, line.p1)):
            print("line not in graph")
        else:
            shape.draw_line(line.p0, line.p1)


for i in range(0, len(lines)):
    line0 = lines[i]
    for j in range(i + 1, len(lines)):
        line1 = lines[j]
        intersection = line0.intersection(line1, 5.0)

        if intersection != None:
            print("lines intersect")
            shape.draw_line(line0.p0, line0.p1)
            shape.draw_line(line1.p0, line1.p1)
            shape.draw_circle(intersection, 4)


shape.finish()
shape.commit()
outpdf.save("example_orgcharts/reconstructed_lines.pdf")
