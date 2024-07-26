from concurrent.futures import Executor, ThreadPoolExecutor
from dataclasses import dataclass
from importlib import resources
import itertools
import json
import logging
import os
from typing import Any, Iterator, Optional

import spacy
from spacy.language import Language
from spacy.lang.char_classes import LATIN_LOWER_BASIC, LATIN_UPPER_BASIC
from spacy.matcher import Matcher, PhraseMatcher
from spacy.pipeline import EntityRuler
from spacy.tokens import Doc, Span, Token

from orgxtract.semantic_analysis import SemanticAnalysis
from . import data

DEBUG = True

logger = logging.getLogger(__package__)

@dataclass(slots=True)
class TextPipeline:
    nlp: Language
    analyser: Optional[SemanticAnalysis]
    executor: Optional[Executor]

    def __init__(
            self,
            data_path: Optional[str] = None,
            llm_model: Optional[str] = None,
            llm_key: Optional[str] = None,
            n_threads: Optional[int] = None):
        nlp = spacy.load("de_core_news_md",
                         exclude=["lemmatizer", "parser", "ner"])

        # There are many abbreviations for common words.
        with open_resource(data_path, "special_cases.jsonl") as file:
            for line in file:
                special_case = json.loads(line)
                nlp.tokenizer.add_special_case(special_case["ORTH"], [special_case])

        nlp.add_pipe("token_normalizer", after="tok2vec")
        nlp.add_pipe("line_break_resolver", after="tagger")
        nlp.add_pipe("org_entity_marker", config={"data_path": data_path})

        self.nlp = nlp
        self.analyser = None
        self.executor = None

        components = nlp.pipe_names

        if llm_model != None:
            try:
                with open_resource(data_path, "schema.json") as file:
                    schema = str(json.load(file))

                    if n_threads != None and 0 < n_threads:
                        self.executor = ThreadPoolExecutor(max_workers=n_threads)

                    self.analyser = SemanticAnalysis(llm_model, llm_key, schema)
    
                components = nlp.pipe_names + [llm_model]
            except Exception as error:
                logger.error("LLM initialisation failed: %s(%s)",
                             type(error).__name__, error)

        logger.info("Text Pipeline selected: %s", "|".join(components))

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.close()
      
    def pipe(self, texts: Iterator[str]):
        def run_analyser(content):
            (text, ents) = content
            try:
                return self.analyser.analyse(text, ents)
            except Exception as error:
                logger.error("Analysis failed: %s(%s)}", type(error).__name__, error)
                return ents

        contents = (sort_ents(doc) for doc in self.nlp.pipe(texts, n_process=1))

        if self.analyser != None:    
            if self.executor != None:
                return self.executor.map(run_analyser, contents)
            else:
                return map(run_analyser, contents)
        else:
            return (ents for (_, ents) in contents)

    def close(self):
        if self.executor != None:
            self.executor.shutdown(cancel_futures=True)

@Language.factory("token_normalizer")
def token_normalizer(nlp: Language, name: str):
    matcher = Matcher(nlp.vocab, validate=DEBUG)
    # Female posts do have the suffix 'in but like many things it was never
    # standardized and we got organigrams with 'n.
    matcher.add("APOSTROPHE", [
        [{}, {"NORM": "'"}, {}],
        [{}, {"TEXT": "’n"}]
    ])

    def normalize(doc):
        matches = matcher(doc)

        if len(matches) == 0:
            return doc

        words = list()
        spaces = list()
        last_end = 0

        def add_token(text: str, space: bool):
            words.append(text)
            spaces.append(space)

        for (_, start, end) in matches:
            start = max(start, last_end)
            span0 = doc[last_end:start]
            span1 = doc[start:end]

            for token in span0:
                add_token(token.text, 0 < len(token.whitespace_))
            
            needs_merge = False
            for token in span1:
                if token.text == "’n":
                    words[-1] += "'n"
                    spaces[-1] = 0 < len(token.whitespace_)
                elif token.norm_ == "'":
                    words[-1] += "'"
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

    return normalize

@Language.factory("line_break_resolver")
def line_break_resolver(nlp: Language, name: str):
    # https://www.ims.uni-stuttgart.de/documents/ressourcen/korpora/tiger-corpus/annotation/tiger_scheme-syntax.pdf
    MODIFIER = ["ADJA", "ADJD", "ADV"]
    JUNCTIONS = ["KOKOM", "KON", "KOUI", "KOUS"]
    ARTICLE = ["ART"]
    PRONOUNS = ["PDAT", "PDS", "PIAT", "PIDAT", "PIS", "PPER", "PPOSAT", "PPOSS", "PRELAT", "PRELS", "PRF", "PWAT", "PWAV", "PWS"]
    POSITIONS = ["APPO", "APPR", "APPRART", "APZR"]
    NOUN_LINKERS = POSITIONS + MODIFIER + JUNCTIONS + PRONOUNS + ARTICLE
    STARTS_WITH_LOWER = f"^[{LATIN_LOWER_BASIC}].*"
    STARTS_WITH_UPPER = f"^[{LATIN_UPPER_BASIC}].*"

    matcher = Matcher(nlp.vocab, validate=DEBUG)
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
        last_end = 0

        def add_token(text: str, space: bool):
            words.append(text)
            spaces.append(space)

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

Token.set_extension("is_org_type", default=False)
Token.set_extension("is_per_prefix", default=False)
Token.set_extension("is_per_post", default=False)

Token.set_extension("is_per", getter=lambda token: (token._.is_per_prefix
                                                    or token._.is_per_post))

@Language.factory("org_entity_marker")
def org_entity_marker(nlp: Language, name: str, data_path: Optional[str]):
    term_matcher = PhraseMatcher(nlp.vocab, validate=DEBUG)

    with open_resource(data_path, "org_types") as file:
        patterns = [nlp.make_doc(line.rstrip()) for line in file]
        term_matcher.add("ORG_TYPE", patterns)

    with open_resource(data_path, "per_prefixes") as file:
        patterns = [nlp.make_doc(line.rstrip()) for line in file]
        term_matcher.add("PER_PREFIX", patterns)

    with open_resource(data_path, "per_posts") as file, open_resource(data_path, "per_posts_abbr") as abbr:
        patterns = [nlp.make_doc(line.rstrip()) for line in file]
        patterns += [nlp.make_doc(line.rstrip()) for line in abbr]
        term_matcher.add("PER_POST", patterns)

    term_matcher.add("PER", [nlp.make_doc("N.N."), nlp.make_doc("N. N.")])

    ORG_TYPE = nlp.vocab["ORG_TYPE"]
    PER_PREFIX = nlp.vocab["PER_PREFIX"]
    PER_POST = nlp.vocab["PER_POST"]
    PER = nlp.vocab["PER"]

    entity_matcher = EntityRuler(nlp, name, overwrite_ents=False, validate=DEBUG)
    entity_matcher.add_patterns([
        {"label": "ORG", "pattern": [
            {"_": {"is_org_type": True}}, {"TAG": "_SP", "OP": "?"}, {"POS": {"IN": ["NOUN", "PROPN", "NUM", "X"]}, "OP": "+"}
        ]},
        {"label": "PER", "pattern": [
            {"_": {"is_per": True}, "OP": "+"}, {"POS": {"IN": ["NOUN", "PROPN"]}, "OP": "+"}
        ]},
        {"label": "PER", "pattern": [
            {"_": {"is_per_post": True}, "OP": "+"}, {"TAG": "_SP", "OP": "?"}, {"_": {"is_per": True}, "OP": "*"}, {"TAG": "_SP", "OP": "*"}, {"POS": {"IN": ["NOUN", "PROPN"]}, "OP": "+"}
        ]},
    ])

    def mark(doc):
        term_matches = term_matcher(doc)
        unnamed_persons = []

        for (match_id, start, end) in term_matches:
            if match_id == PER:
                unnamed_persons.append(Span(doc, start, end, "PER"))
                continue

            is_org_type = match_id == ORG_TYPE
            is_per_prefix = match_id == PER_PREFIX
            is_per_post = match_id == PER_POST

            for token in doc[start:end]:
                token._.is_org_type = is_org_type
                token._.is_per_prefix = is_per_prefix
                token._.is_per_post = is_per_post

        doc.set_ents(unnamed_persons)

        doc = entity_matcher(doc)

        return doc

    return mark

def sort_ents(doc):
    content = {"type": None, "name": None, "persons": []}

    for ent in doc.ents:
        if ent.start == 0:
            if ent.label_ == "ORG":
                content["name"] = ent.text.replace("\n\n", " ").replace("\n", " ")

                for token in ent:
                    if token._.is_org_type:
                        if content["type"] == None:
                            content["type"] = token.text
                        else:
                            content["type"] += " " + token.text
            elif ent.label_ == "PER":
                content["name"] = ent.text.replace("\n\n", " ").replace("\n", " ")

                for token in ent:
                    if token._.is_per_post:
                        if content["type"] == None:
                            content["type"] = token.text
                        else:
                            content["type"] += " " + token.text

        if ent.label_ == "PER":
            person = {
                "name": ent.text.replace("\n\n", " ").replace("\n", " "),
                "positionType": None
            }

            for token in ent:
                if token._.is_per_post:
                    if person["positionType"] == None:
                        person["positionType"] = token.text
                    else:
                        person["positionType"] += " " + token.text

            if person["positionType"] != None:
                person["name"] = person["name"].lstrip(person["positionType"]).lstrip()

            content["persons"].append(person)

    if content["type"] == None:
        i = 0
        for token in doc:
            if token._.is_org_type:
                i += 1
            else:
                break

        if 0 < i:
            content["type"] = doc[:i].text
            
    return (doc.text, content)

def open_resource(data_path: Optional[str], resource: str):
    if data_path != None:
        try:
            return open_resource_from_path(data_path, resource)
        except:
            return open_resource_from_package(resource)

    return open_resource_from_package(resource)
            
def open_resource_from_package(resource: str):
    data_resource = resources.files(data) / resource
    return data_resource.open(mode="r", encoding="utf-8")

def open_resource_from_path(data_path: str, resource: str):
    path = os.path.join(data_path, resource)
    return open(path, mode="r", encoding="utf-8")
