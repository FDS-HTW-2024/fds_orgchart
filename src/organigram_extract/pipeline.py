from collections import defaultdict
import json

import spacy
from spacy.language import Language
from spacy.lang.char_classes import LATIN_UPPER_BASIC
from spacy.matcher import Matcher, PhraseMatcher
from spacy.tokens import Doc, Span

from organigram_extract.data import Rect

@Language.factory("merge_textblock")
def merge_textblock(nlp, name):
    matcher = Matcher(nlp.vocab, validate=True)
    LINKING_WORDS = ["APPR", "APPRART", "ART", "KON", "PPOSAT", "PRELAT"]
    matcher.add("SPACE", [
        # Finanzielle\nHilfen
        [{"TAG": {"IN": ["ADJA", "ADJD", "ADV"]}}, {"TEXT": "\n"}, {"TAG": "NN"}],
        # Polizei;\nFeuerweht
        [{}, {"TAG": {"IN": ["$.", "$,"]}, "IS_PUNCT": True}, {"TEXT": "\n"}, {}],
        # Forst- und\nLandwirtschaft
        [{}, {"TAG": {"IN": LINKING_WORDS}, "IS_LOWER": True}, {"TEXT": "\n"}, {}],
        # Forst-\nund Landwirtschaft
        [{}, {"TEXT": "\n"}, {"TAG": {"IN": LINKING_WORDS}, "IS_LOWER": True}, {}],
        # Abteilung A Z 4\n(ohne Referat V 5)
        [{}, {"TEXT": "\n"}, {"TAG": "$("}, {}],
        # Stabstelle /\nLehrgruppe I
        [{}, {"TEXT": {"IN": ["-", "/"]}}, {"TEXT": "\n"}, {}],
        # Stabstelle\n/ Lehrgruppe I
        [{}, {"TEXT": "\n"}, {"TEXT": {"IN": ["-", "/"]}}, {}],
        # These patterns are for long chains of nouns.
        [{"TAG": "NN", "OP": "+"}, {"TEXT": "\n"}, {"TAG": "NN", "OP": "+"}, {"TAG": {"IN": LINKING_WORDS}}, {}],
        [{}, {"TAG": "$.", "IS_PUNCT": True}, {"TAG": "NN", "OP": "+"}, {"TEXT": "\n"}, {"TAG": "NN", "OP": "+"}, {"TAG": "$.", "IS_PUNCT": True}]
    ])
    matcher.add("BREAK", [
        [{"TAG": "TRUNC", "IS_LOWER": True}, {"TEXT": "\n"}, {"IS_LOWER": True}],
        [{"TAG": "TRUNC"}, {"TEXT": "\n"}, {"TAG": {"NOT_IN": LINKING_WORDS}, "IS_LOWER": True}],
        [{"TEXT": {"REGEX": f"[{LATIN_UPPER_BASIC}]" + r"(\w)*-$"}}, {"TEXT": "\n"}, {"TAG": {"NOT_IN": LINKING_WORDS}, "IS_LOWER": True}],
    ])
    matcher.add("COMBO", [
        [{"TAG": "TRUNC"}, {"TEXT": "\n"}, {"IS_TITLE": True}],
    ])
    SPACE = nlp.vocab["SPACE"]
    BREAK = nlp.vocab["BREAK"]
    COMBO = nlp.vocab["COMBO"]

    def merge(doc):
        matches = matcher(doc)

        if len(matches) == 0:
            return doc

        words = list()
        spaces = list()

        def add_token(text: str, space: bool):
            words.append(text)
            spaces.append(space)

        last_end = 0
        for (match_id, start, end) in matches:
            start = max(start, last_end)
            span0 = doc[last_end:start]
            span1 = doc[start:end]

            for token in span0:
                add_token(token.text, 0 < len(token.whitespace_))

            if match_id == SPACE:
                for token in span1:
                    if token.text == "\n":
                        spaces[-1] = True
                    else:
                        add_token(token.text, 0 < len(token.whitespace_))
            elif match_id == BREAK:
                needs_merge = False
                for token in span1:
                    if token.text == "\n":
                        needs_merge = True
                    elif needs_merge:
                        words[-1] = words[-1].rstrip("-") + token.text
                        spaces[-1] = 0 < len(token.whitespace_)
                        needs_merge = False
                    else:
                        add_token(token.text, 0 < len(token.whitespace_))
            elif match_id == COMBO:
                needs_merge = False
                for token in span1:
                    if token.text == "\n":
                        needs_merge = True
                    elif needs_merge:
                        words[-1] += token.text
                        spaces[-1] = 0 < len(token.whitespace_)
                        needs_merge = False
                    else:
                        add_token(token.text, 0 < len(token.whitespace_))

            last_end = end

        for token in doc[last_end:]:
            add_token(token.text, 0 < len(token.whitespace_))

        return nlp(Doc(nlp.vocab, words, spaces))

    return merge


def something_text(content_nodes):
    nlp = spacy.load("de_core_news_lg")
    # There are many abbreviations for common words.
    nlp.tokenizer.add_special_case("einschl.", [{"ORTH": "einschl.", "NORM": "einschließlich"}])
    nlp.tokenizer.add_special_case("insbes.", [{"ORTH": "insbes.", "NORM": "insbesondere"}])
    nlp.tokenizer.add_special_case("intern.", [{"ORTH": "intern.", "NORM": "international"}])

    nlp.add_pipe("merge_textblock", after="tagger")
    print(nlp.pipe_names)


    # TODO: Create text block iter for nlp.pipe text stream
    # Merge text lines that are next to each other
    for node in content_nodes:
        text_block = node.block

        for index in reversed(range(1, len(text_block))):
            line_j = text_block[index]
            line_i = text_block[index - 1]

            if (abs(line_j.bbox.x0 - line_i.bbox.x1) < 0.5
                    and abs(line_j.bbox.y1 - line_i.bbox.y1) < 0.5):
                line_i.text += line_j.text
                line_i.bbox = Rect._replace(line_i.bbox, x1= max(line_i.bbox.x1, line_j.bbox.x1))
                text_block.pop(index)

    # input = "Referat Z A 4\nGrundsatz-\nangelegenheiten\nPersonal des BMF;\nFortbildung im BMF;\nDisziplinarangele-\ngenheiten\nMR Budig\nDemographie-Beraterin\nfür das BMF"
    # doc = nlp(input)

    for node in content_nodes:
      input = "\n".join([line.text for line in node.block])
      doc = nlp(input)

      print("=================")
      print(repr(input))
      print(doc.text)
      print([(token.text, token.tag_) for token in doc])
      # print([(token.text, token.label_) for token in doc.ents])

import pymupdf
from extract import extract, debug_page

page = pymupdf.open("example_orgcharts/bmf-orgplan_11_november_2010.pdf")[0]
page.remove_rotation()
(rectangles, lines, junctions, words, content_nodes) = extract(page)
debug_page(page, rectangles, lines, words, content_nodes)
# something_text(content_nodes)
