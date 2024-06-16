import fitz
import spacy
from spacy import displacy
import array
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
lines: list[Line] = list()
content_nodes: list[ContentNode] = list()

word_blocks = page.get_text("blocks", sort=True)  # list of words on page

words = list(map(lambda word: word[4].strip().replace("\n", " "), word_blocks))

puncs = "!()-[]{}:;"'/'",<>?@#%&*_~''"

clean_words = [''.join(char for char in word if char not in puncs)
               for word in words]

print(clean_words)
nlp = spacy.load("de_core_news_lg")
docs = list(nlp.pipe(clean_words))
displacy.serve(docs, style="ent")
