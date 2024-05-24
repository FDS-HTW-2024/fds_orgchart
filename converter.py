import fitz
from math import sqrt
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
rect_list = list()
words = page.get_text("blocks", sort=True)  # list of words on page
lines_list = list()

for d in drawings_list:
    for item in d["items"]:
        match item[0]:
            case "re":
                rect_list.append(item[1])
            case "l":
                lines_list.append((Point._make(item[1]), Point._make(item[2])))
            case _:
                pass

print(len(lines_list))
# create ContentNodes
for rect in rect_list:
    rectangle = Rectangle(
        top_left=Point(rect.x0, rect.y0),
        bottom_right=Point(rect.x1, rect.y1))
    rect_words = [w for w in words if fitz.Rect(
        w[:4]).intersects(rect)]
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


# Function to calculate the Euclidean distance between two points
def distance(p1, p2):
    return sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


# Function to check if two points are within a threshold distance
def within_threshold(p1, p2, threshold):
    return distance(p1, p2) <= threshold


def line_intersection(line1, line2, tolerance=5):
    (x1, y1), (x2, y2) = line1
    (x3, y3), (x4, y4) = line2

    denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
    if denom == 0:
        # Check if endpoints are within the tolerance
        if within_threshold((x1, y1), (x3, y3), tolerance) or within_threshold((x1, y1), (x4, y4), tolerance) or \
           within_threshold((x2, y2), (x3, y3), tolerance) or within_threshold((x2, y2), (x4, y4), tolerance):
            return True  # Treat as intersecting due to close endpoints
        return None  # Parallel lines with no intersection

    ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom
    ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denom

    if 0 <= ua <= 1 and 0 <= ub <= 1:
        x = x1 + ua * (x2 - x1)
        y = y1 + ua * (y2 - y1)
        return (x, y)

    return None

# Kurbo Library Source: https://github.com/linebender/kurbo/blob/884483b3de412c7c10e2fff4f43dbe96304c0dbd/src/line.rs#L44
def get_line_intersection(line0, line1, threshold = 5.0):
    lengthAB = sqrt(pow(line0.p1.x - line0.p0.x, 2) + pow(line0.p1.y - line0.p0.y, 2))
    lengthCD = sqrt(pow(line1.p1.x - line1.p0.x, 2) + pow(line1.p1.y - line1.p0.y, 2))

    normalized_ab = Point((line0.p1.x - line0.p0.x) / lengthAB, (line0.p1.y - line0.p0.y) / lengthAB)
    normalized_cd = Point((line1.p1.x - line1.p0.x) / lengthCD, (line1.p1.y - line1.p0.y) / lengthCD)

    a = Point(line0.p1.x - normalized_ab.x * (lengthAB + threshold), line0.p1.y - normalized_ab.y * (lengthAB + threshold))
    b = Point(line0.p0.x + normalized_ab.x * (lengthAB + threshold), line0.p0.y + normalized_ab.y * (lengthAB + threshold))
    c = Point(line1.p1.x - normalized_cd.x * (lengthCD + threshold), line1.p1.y - normalized_cd.y * (lengthCD + threshold))
    d = Point(line1.p0.x + normalized_cd.x * (lengthCD + threshold), line1.p0.y + normalized_cd.y * (lengthCD + threshold))

    ab = Point(b.x - a.x, b.y - a.y)
    cd = Point(d.x - c.x, d.y - c.y)
    ab_cross_cd = ab.x * cd.y - ab.y * cd.x

    if ab_cross_cd == 0.0:
        return None

    ac = Point(a.x - c.x, a.y - c.y)
    ab_cross_ac = ab.x * ac.y - ab.y * ac.x
    h = ab_cross_ac / ab_cross_cd

    return Point(c.x + cd.x * h, c.y + cd.y * h)

def is_node_point(rect, point, threshold = 1.0):
    (x0, y0, x1, y1) = rect
    rect2 = (x0 - threshold, y0 - threshold, x1 + threshold, y1 + threshold)
    return fitz.Rect(rect2).contains(point)

node_points = []
graph_lines = []

for rect in rect_list:
    shape.draw_rect(rect)
    for line in lines_list:
        if is_node_point(rect, line[0]):
            print("intersects")
            shape.draw_circle(line[0], 4)
            node_points.append(Point._make(line[0]))
        if is_node_point(rect, line[1]):
            print("intersects")
            shape.draw_circle(line[1], 4)
            node_points.append(Point._make(line[1]))
        if (not is_node_point(rect, line[0]) and
                not is_node_point(rect, line[1])):
            print("line not in graph")
        else:
            shape.draw_line(line[0], line[1])


for i in range(0, len(lines_list)):
    line1 = lines_list[i]
    for j in range(0, len(lines_list)):
        if i == j:
            continue

        line2 = lines_list[j]
        intersection = get_line_intersection(Line(line1[0], line1[1]), Line(line2[0], line2[1]))
        if intersection:
            print("lines intersect")
            shape.draw_circle(intersection, 4)


shape.finish()
shape.commit()
outpdf.save("example_orgcharts/reconstructed_lines.pdf")
