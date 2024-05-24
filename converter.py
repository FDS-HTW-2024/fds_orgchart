import fitz
import pprint
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

# for d in drawings_list:
#     if d["items"][0][0] == "re":
#         print(d["items"][0])
#         print("---------")
#     elif d["items"][0][0] == "l":
#         print(d["items"][0])
#         print("---------")

rect_list = [x for x in drawings_list if x["items"][0][0] == "re"]
words = page.get_text("blocks", sort=True)  # list of words on page

lines_list = [x["items"] for x in drawings_list if x["items"][0][0] == "l"]
print(len(lines_list))
# create ContentNodes
for rect in rect_list:
    rect_tuple = rect["items"][0]
    rectangle = Rectangle(
        top_left=Point(rect_tuple[1].x0, rect_tuple[1].y0),
        bottom_right=Point(rect_tuple[1].x1, rect_tuple[1].y1))
    rect_words = [w for w in words if fitz.Rect(
        w[:4]).intersects(rect_tuple[1])]
    text_blocks = list()
    for (x0, y0, x1, y1, word, _, _) in rect_words:
        text_block = TextBlock(bounding_box=Rectangle(
            Point(x0, y0), Point(x1, y1)), content=word)
        text_blocks.append(text_block)
    content_node = ContentNode(rect=rectangle, content=text_blocks)
    print(content_node)
    print("################")

outpdf = fitz.open()
outpage = outpdf.new_page(width=page.rect.width, height=page.rect.height)
shape = outpage.new_shape()


def line_intersects(line0, line1):

    return False


def get_node_points(rect, line):
    (x0, y0, x1, y1) = rect
    (x0, y0, x1, y1) = (x0 - 1, y0 - 1, x1 + 1, y1 + 1)

    topleft_bottomleft = Line(Point(x0, y0), Point(x0, y1))
    topleft_topright = Line(Point(x0, y0), Point(x1, y0))
    bottomright_bottomleft = Line(Point(x0, y1), Point(x1, y1))
    bottomright_topright = Line(Point(x1, y0), Point(x1, y1))

    return (line_intersects(topleft_bottomleft, line) or
            line_intersects(topleft_topright, line) or
            line_intersects(bottomright_bottomleft, line) or
            line_intersects(bottomright_topright, line))


for line in lines_list:
    for line_segment in line:
        shape.draw_line(line_segment[1], line_segment[2])

for rect in rect_list:
    shape.draw_rect(rect["items"][0][1])
    for line in lines_list:
        for line_segment in line:
            if get_node_points(rect["items"][0][1],
                             Line(Point._make(line_segment[1]),
                                  Point._make(line_segment[2]))):
                print("intersects")
                shape.draw_circle(line_segment[1], 4)


shape.finish()
shape.commit()
outpdf.save("example_orgcharts/reconstructed_lines.pdf")
