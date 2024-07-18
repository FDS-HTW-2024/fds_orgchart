from dataclasses import dataclass
import itertools
from typing import Any, Iterator, Optional

import spacy
from spacy.language import Language
from spacy.lang.char_classes import LATIN_LOWER_BASIC, LATIN_UPPER_BASIC
from spacy.matcher import Matcher, PhraseMatcher
from spacy.tokens import Doc, Token

@dataclass(slots=True)
class TextPipeline:
    nlp: Language

    def __init__(self, config: dict[str, Any] = {}):
        nlp = spacy.load("de_core_news_lg",
                         exclude=["morphologizer", "parser", "lemmatizer", "ner"])
        # There are many abbreviations for common words.
        nlp.tokenizer.add_special_case("einschl.", [{"ORTH": "einschl.", "NORM": "einschließlich"}])
        nlp.tokenizer.add_special_case("insbes.", [{"ORTH": "insbes.", "NORM": "insbesondere"}])
        nlp.tokenizer.add_special_case("m.d.W.d.G.b.", [{"ORTH": "m.d.W.d.G.b.", "NORM": "mit der Wahrnehmung der Geschäfte betraut"}])
        nlp.tokenizer.add_special_case("m. d. W. d. G. b.", [{"ORTH": "m. d. W. d. G. b.", "NORM": "mit der Wahrnehmung der Geschäfte betraut"}])

        nlp.add_pipe("line_break_resolver")
        print(nlp.pipe_names)

        self.nlp = nlp

    def add_llm_ner(config: dict[str, Any]):
        # TODO: Add llm component from semantic analysis
        pass

    def process(self, text: str):
        # Language.pipe does not deal well with sporadic infinite generators.
        # So, we use the Language object directly.
        doc = self.nlp(text)
        result = doc.text

        return result

@Language.factory("line_break_resolver")
def line_break_resolver(nlp, name):
    # https://www.ims.uni-stuttgart.de/documents/ressourcen/korpora/tiger-corpus/annotation/tiger_scheme-syntax.pdf
    MODIFIER = ["ADJA", "ADJD", "ADV"]
    JUNCTIONS = ["KOKOM", "KON", "KOUI", "KOUS"]
    ARTICLE = ["ART"]
    PRONOUNS = ["PDAT", "PDS", "PIAT", "PIDAT", "PIS", "PPER", "PPOSAT", "PPOSS", "PRELAT", "PRELS", "PRF", "PWAT", "PWAV", "PWS"]
    POSITIONS = ["APPO", "APPR", "APPRART", "APZR"]
    NOUN_LINKERS = POSITIONS + MODIFIER + JUNCTIONS + PRONOUNS + ARTICLE
    STARTS_WITH_LOWER = f"^[{LATIN_LOWER_BASIC}].*"
    STARTS_WITH_UPPER = f"^[{LATIN_UPPER_BASIC}].*"

    matcher = Matcher(nlp.vocab, validate=True)
    matcher.add("SLASH", [
        [{}, {"TEXT": "/"}, {"TEXT": "\n"}, {}],
        [{}, {"TEXT": "\n"}, {"TEXT": "/"}, {}],
    ])
    matcher.add("COMBO", [
        # Dipl.-\nIng.
        [{"TAG": "TRUNC"}, {"TEXT": "\n"}, {"TEXT": {"REGEX": STARTS_WITH_UPPER}}],
        [{"TEXT": {"REGEX": STARTS_WITH_UPPER + "-$"}}, {"TEXT": "\n"}, {"TEXT": {"REGEX": STARTS_WITH_UPPER}}],
        # Import\n-Export-\nRegelung
        [{"TEXT": {"REGEX": f"^-[{LATIN_UPPER_BASIC}].*-$"}}, {"TEXT": "\n"}, {"TEXT": {"REGEX": STARTS_WITH_UPPER}}],
    ])
    matcher.add("BREAK", [
        # Umsatz-\nsteuer; inter-\national
        [{"TAG": "TRUNC"}, {"TEXT": "\n"}, {"TAG": {"NOT_IN": JUNCTIONS}, "TEXT": {"REGEX": STARTS_WITH_LOWER}}],
        [{"TEXT": {"REGEX": r"^(\w).*-$"}}, {"TEXT": "\n"}, {"TAG": {"NOT_IN": JUNCTIONS}, "TEXT": {"REGEX": STARTS_WITH_LOWER}}],
        # Werkzeugmaschinen-Import- und ‑Export-\ngeschäfte
        [{"TEXT": {"REGEX": r"^-(\w).*-$"}}, {"TEXT": "\n"}, {"TAG": {"NOT_IN": JUNCTIONS}, "TEXT": {"REGEX": STARTS_WITH_LOWER}}],
        # inter\n-national
        [{"TAG": {"NOT_IN": JUNCTIONS}}, {"TEXT": "\n"}, {"TEXT": {"REGEX": r"^-(\w).*"}}]
    ])
    matcher.add("SPACE", [
        [{"TAG": {"IN": MODIFIER}}, {"TEXT": "\n"}, {}],
        [{}, {"TAG": {"IN": ["$.", "$,"]}, "IS_PUNCT": True}, {"TEXT": "\n"}, {}],
        [{}, {"TAG": {"IN": NOUN_LINKERS}, "IS_LOWER": True, "OP": "+"}, {"TEXT": "\n"}, {}],
        [{}, {"TEXT": "\n"}, {"TAG": {"IN": NOUN_LINKERS}, "IS_LOWER": True, "OP": "+"}, {}],
        [{}, {"TEXT": "\n"}, {"TAG": "$("}, {}],
        # Similar to tag '$(' but without parentheses
        [{"TEXT": {"REGEX": "^[-–—]$"}}, {"TEXT": "\n"}, {}],
        # It is impossible to figure out with only pattern matching if two
        # nouns separated by a newline are one. So, we don't even try except
        # when there is a 'sentence' where a semicolon is the period.
        [{"TEXT": ";"}, {"OP": "+"}, {"TEXT": "\n"}, {"OP": "+"}, {"TEXT": ";"}],
        [{"TEXT": "\n\n"}, {"OP": "+"}, {"TEXT": "\n"}, {"OP": "+"}, {"TEXT": ";"}],
        [{"TEXT": ";"}, {"OP": "+"}, {"TEXT": "\n"}, {"OP": "+"}, {"TEXT": "\n\n"}],
    ])

    SPACE = nlp.vocab["SPACE"]
    BREAK = nlp.vocab["BREAK"]
    COMBO = nlp.vocab["COMBO"]
    SLASH = nlp.vocab["SLASH"]

    def resolve(doc):
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
                # print("SPACE")
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
                        words[-1] = words[-1].rstrip("-") + token.text.lstrip("-")
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
            elif match_id == SLASH:
                for token in span1:
                    if token.text == "/":
                        add_token(token.text, spaces[-1])
                    elif token.text != "\n":
                        add_token(token.text, 0 < len(token.whitespace_))

            last_end = end

        for token in doc[last_end:]:
            add_token(token.text, 0 < len(token.whitespace_))

        return nlp(Doc(nlp.vocab, words, spaces))

    return resolve
