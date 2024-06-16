import spacy
from spacy import displacy
from data import Rectangle, TextBlock, ContentNode, Point

rect = Rectangle(Point(0, 0), Point(10, 10))
text_blocks = list()
text_blocks.append("Abteilung Z")
text_blocks.append("Zentralabteilung")
text_blocks.append("MD'in Dr. Stahl-Hoepner")

content_nodes: list[ContentNode] = list()
content_nodes.append(ContentNode(rect, text_blocks))

words = list(map(lambda word: word[4].strip().replace("\n", " "), word_blocks))

puncs = "!()-[]{}:;"'/'",<>?@#%&*_~''"

clean_words = [''.join(char for char in word if char not in puncs)
               for word in words]

print(clean_words)
nlp = spacy.load("de_core_news_lg")
docs = list(nlp.pipe(clean_words))
displacy.serve(docs, style="ent")
