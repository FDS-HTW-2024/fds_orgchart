from dataclasses import dataclass
import itertools
import json
from importlib import resources
from typing import Any, Iterator, Optional

import spacy
from spacy.language import Language
from spacy.lang.char_classes import LATIN_LOWER_BASIC, LATIN_UPPER_BASIC
from spacy.matcher import Matcher, PhraseMatcher
from spacy.tokens import Doc, Token

from . import data

DATA_PATH = resources.files(data)

@dataclass(slots=True)
class TextPipeline:
    nlp: Language

    def __init__(self, config: dict[str, Any] = {"validate": True}):
        nlp = spacy.load("de_core_news_lg",
                         exclude=["morphologizer", "parser", "ner"])

        # There are many abbreviations for common words.
        with open(DATA_PATH / "special_cases.jsonl") as file:
            for line in file:
                special_case = json.loads(line)
                nlp.tokenizer.add_special_case(special_case["ORTH"], [special_case])

        nlp.add_pipe("line_break_resolver", after="tagger", config=config)
        nlp.add_pipe("org_entity_marker", config=config)

        ruler = nlp.add_pipe("span_ruler", config=config)
        ruler.add_patterns([
            {"label": "ORG", "pattern": [
                {"_": {"is_org_type": True}}, {"TAG": {"NOT_IN": ["_SP"]}, "OP": "+"}
            ]},
            {"label": "PER", "pattern": [
                {"_": {"is_per_prefix": True}}, {"TAG": {"NOT_IN": ["_SP"]}, "OP": "+"}
            ]},
        ])

        print(nlp.pipe_names)

        # TODO: Read config to create llm ner if available.
        self.nlp = nlp

    def process(self, texts: Iterator[str]):
        ORG = self.nlp.vocab["ORG"]
        PER = self.nlp.vocab["PER"]

        for doc in self.nlp.pipe(texts):
            result = {
                "type": None,
                "name": None,
                "persons": [],
                "responsibilities": []
            }

            start = 0
            end = 0
            # TODO: Find more elegant solution to collapse spans
            for ent in doc.spans["ruler"]:
                for token in ent:
                    if ent.label == ORG and token._.is_org_type and result["type"] == None:
                        result["type"] = token.lemma_
                        result["name"] = ent.text
                        break

                    if ent.label == PER and token._.is_per_prefix:
                        if start == ent.start and end < ent.end:
                            result["persons"][-1]["name"] = ent.text
                        elif end <= ent.start:
                            result["persons"].append({
                                "name": ent.text,
                                "positionType": token.text,
                            })
                        start = ent.start
                        end = ent.end
                        break

            yield result

@Language.factory("line_break_resolver")
def line_break_resolver(nlp: Language, name: str, validate: bool):
    # https://www.ims.uni-stuttgart.de/documents/ressourcen/korpora/tiger-corpus/annotation/tiger_scheme-syntax.pdf
    MODIFIER = ["ADJA", "ADJD", "ADV"]
    JUNCTIONS = ["KOKOM", "KON", "KOUI", "KOUS"]
    ARTICLE = ["ART"]
    PRONOUNS = ["PDAT", "PDS", "PIAT", "PIDAT", "PIS", "PPER", "PPOSAT", "PPOSS", "PRELAT", "PRELS", "PRF", "PWAT", "PWAV", "PWS"]
    POSITIONS = ["APPO", "APPR", "APPRART", "APZR"]
    NOUN_LINKERS = POSITIONS + MODIFIER + JUNCTIONS + PRONOUNS + ARTICLE
    STARTS_WITH_LOWER = f"^[{LATIN_LOWER_BASIC}].*"
    STARTS_WITH_UPPER = f"^[{LATIN_UPPER_BASIC}].*"

    matcher = Matcher(nlp.vocab, validate=validate)
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

@Language.factory("org_entity_marker")
def org_entity_marker(nlp: Language, name: str, validate: bool):
    Token.set_extension("is_org_type", default=False)
    Token.set_extension("is_per_prefix", default=False)

    term_matcher = PhraseMatcher(nlp.vocab, attr="LEMMA", validate=validate)

    with nlp.select_pipes(enable=["lemmatizer"]):
        with open(DATA_PATH / "org_types") as file:
            patterns = [nlp(line.rstrip()) for line in file]
            term_matcher.add("ORG_TYPE", patterns)

        with open(DATA_PATH / "per_prefixes") as file:
            patterns = [nlp(line.rstrip()) for line in file]
            term_matcher.add("PER_PREFIX", patterns)

    ORG_TYPE = nlp.vocab["ORG_TYPE"]
    PER_PREFIX = nlp.vocab["PER_PREFIX"]

    def mark(doc):
        matches = term_matcher(doc)

        for (match_id, start, end) in matches:
            for token in doc[start:end]:
                token._.is_org_type = match_id == ORG_TYPE
                token._.is_per_prefix = match_id == PER_PREFIX

        return doc

    return mark
