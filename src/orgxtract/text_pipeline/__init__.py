from concurrent.futures import Executor, ThreadPoolExecutor
from dataclasses import dataclass
from enum import auto, IntFlag
from importlib import resources
import itertools
import json
import logging
import os
from typing import Iterator, Optional

import spacy
from spacy.language import Language
from spacy.matcher import Matcher, PhraseMatcher
from spacy.pipeline import EntityRuler
from spacy.tokens import Doc, Span, Token

from .cleaning import line_break_resolver, token_normalizer
from .semantic_analysis import SemanticAnalysis
from orgxtract import data

logger = logging.getLogger(__package__)

@dataclass(slots=True)
class TextPipeline:
    """A pipeline to extract structured data from text

    The TextPipeline takes care of threading, integration of LLMs and most
    importantly the conversion of recognised named entities into a data
    format made for further analysis.
    """

    nlp: Language
    analyser: Optional[SemanticAnalysis]
    executor: Optional[Executor]

    def __init__(
            self,
            data_path: Optional[str] = None,
            llm_model: Optional[str] = None,
            llm_key: Optional[str] = None,
            n_threads: Optional[int] = None):
        """Creates a new TextPipeline

        To use an LLM as named entity recognition (NER) system, only the name
        of the model and optionally the key if it is a remote LLM need to be
        provided. For remote LLMs using multiple threads can lead to a
        significant speed boost because many requests can be sent at the
        same time.

        The data set used to find organigram entities can be configured by
        providing a path to a folder containing files for the:
          - schema (schema.json),
          - organisation types (org_types),
          - positions within an organization (per_positions) and abbreviations
            (per_positions_abbr),
          - salutations (per_salutations) and
          - titles for a person (per_titles).

        By default the data path is set to the data module. Those files can
        be used as basis for your custom files. However, it is not necessary
        to provide every file.

        Note that you should not change the structure of the schema but modify
        the enums only.
        """

        nlp = spacy.load("de_core_news_md",
                         exclude=["parser", "lemmatizer", "attribute_ruler", "ner"])

        # There are many abbreviations for common words.
        with open_resource(data_path, "special_cases.jsonl") as file:
            for line in file:
                special_case = json.loads(line)
                nlp.tokenizer.add_special_case(special_case["ORTH"], [special_case])

        nlp.add_pipe("token_normalizer", after="tok2vec")
        nlp.add_pipe("line_break_resolver", after="tagger")
        nlp.add_pipe("orgxtract_tagger", config={"data_path": data_path})
        nlp.add_pipe("orgxtract_ruler")

        self.nlp = nlp
        self.analyser = None
        self.executor = None

        components = nlp.pipe_names

        if llm_model != None:
            try:
                with open_resource(data_path, "schema.json") as file:
                    schema = json.dumps(json.load(file),
                                        ensure_ascii=False,
                                        separators=(",", ":"))

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
        """Returns an iterator yielding dictionaries with the extracted data

        The extracted data is roughly in the form of the JSON format.

        {
            "type": string,
            "name": string,
            "date": string,
            "persons": [
                {
                    "positionType": string,
                    "salutation": string,
                    "title": string,
                    "name": string,
                },
                ...
            ]
        }

        Fields can be None or non-existent. Properly check the key before!
        """

        contents = self.nlp.pipe(texts, n_process=1)

        if self.analyser != None:
            if self.executor != None:
                futures = [(doc, self.executor.submit(self.analyser.analyse, doc.text))
                           for doc in contents]

                for (doc, future) in futures:
                    ents = entities_to_dict(doc)

                    try:
                        yield merge_dicts(ents, future.result())
                    except Exception as error:
                        logger.error("Analysis failed: %s(%s)}", type(error).__name__, error)
                        yield ents
            else:
                for doc in contents:
                    ents = entities_to_dict(doc)

                    try:
                        yield merge_dicts(ents, self.analyser.analyse(doc.text))
                    except Exception as error:
                        logger.error("Analysis failed: %s(%s)}", type(error).__name__, error)
                        yield ents
        else:
            for doc in contents:
                yield entities_to_dict(doc)

    def close(self):
        """Frees any allocated resources

        This frees the resources used for the thread pool. It is, however,
        better to use Python's with statement instead of calling this
        function manually.            
        """

        if self.executor != None:
            self.executor.shutdown(cancel_futures=True)

class OrgX(IntFlag):
    NONE = 0
    ORG_TYPE = auto()
    PER_POSITION = auto()
    PER_SALUTATION = auto()
    PER_TITLE = auto()
    PER_NN = auto()
    ORG = ORG_TYPE
    PER = PER_POSITION | PER_SALUTATION | PER_TITLE | PER_NN

Token.set_extension("orgx", default=OrgX.NONE)
Token.set_extension("is_orgx_org",
                    getter=lambda token: token._.orgx & OrgX.ORG != OrgX.NONE)
Token.set_extension("is_orgx_per",
                    getter=lambda token: token._.orgx & OrgX.PER != OrgX.NONE)

@Language.factory("orgxtract_tagger")
def orgxtract_tagger(nlp: Language, name: str, data_path: Optional[str]):
    term_matcher = PhraseMatcher(nlp.vocab, validate=True)

    with open_resource(data_path, "org_types") as file:
        patterns = [nlp.make_doc(line.rstrip()) for line in file]
        term_matcher.add("ORG_TYPE", patterns)

    with open_resource(data_path, "per_positions") as file, open_resource(data_path, "per_positions_abbr") as abbr:
        patterns = [nlp.make_doc(line.rstrip()) for line in file]
        patterns += [nlp.make_doc(line.rstrip()) for line in abbr]
        term_matcher.add("PER_POSITION", patterns)

    with open_resource(data_path, "per_salutations") as file:
        patterns = [nlp.make_doc(line.rstrip()) for line in file]
        term_matcher.add("PER_SALUTATION", patterns)

    with open_resource(data_path, "per_titles") as file:
        patterns = [nlp.make_doc(line.rstrip()) for line in file]
        term_matcher.add("PER_TITLE", patterns)

    term_matcher.add("PER_NN", [nlp.make_doc("N.N."), nlp.make_doc("N. N.")])

    ORG_TYPE = nlp.vocab["ORG_TYPE"]
    PER_POSITION = nlp.vocab["PER_POSITION"]
    PER_SALUTATION = nlp.vocab["PER_SALUTATION"]
    PER_TITLE = nlp.vocab["PER_TITLE"]
    PER_NN = nlp.vocab["PER_NN"]

    filler = Matcher(nlp.vocab, validate=True)
    filler.add("SPACE", [
        [{"_": {"is_orgx_org": True}}, {"TAG": "_SP", "OP": "+"}, {"_": {"is_orgx_org": True}}],
        [{"_": {"is_orgx_per": True}}, {"TAG": "_SP", "OP": "+"}, {"_": {"is_orgx_per": True}}],
    ])

    def tag(doc: Doc):
        for (match_id, start, end) in term_matcher(doc):
            tag = OrgX.NONE

            if match_id == ORG_TYPE:
                tag = OrgX.ORG_TYPE
            elif match_id == PER_POSITION:
                tag = OrgX.PER_POSITION
            elif match_id == PER_SALUTATION:
                tag = OrgX.PER_SALUTATION
            elif match_id == PER_TITLE:
                tag = OrgX.PER_TITLE
            elif match_id == PER_NN:
                tag = OrgX.PER_NN

            for token in doc[start:end]:
                token._.orgx = tag

        for (_match_id, start, end) in filler(doc):
            tag = doc[start]._.orgx

            for token in doc[start + 1:end - 1]:
                token._.orgx = tag

        return doc

    return tag

Span.set_extension("orgx", default=())

@Language.factory("orgxtract_ruler")
def orgxtract_ruler(nlp: Language, name: str):
    entity_ruler = EntityRuler(nlp, name, overwrite_ents=False, validate=True)
    entity_ruler.add_patterns([
        {"label": "ORG", "pattern": [
            {"_": {"orgx": OrgX.ORG_TYPE}}, {"TAG": "_SP", "OP": "?"}, {"_": {"is_orgx_per": False}, "POS": {"IN": ["NOUN", "PROPN", "NUM", "X", "ADP", "CCONJ", "DET"]}, "OP": "+"}
        ]},
        {"label": "PER", "pattern": [{"_": {"orgx": OrgX.PER_NN}, "OP": "+"}]},
        {"label": "PER", "pattern": [
            {"_": {"is_orgx_per": True}, "OP": "+"}, {"TAG": "_SP", "OP": "?"}, {"POS": {"IN": ["NOUN", "PROPN"]}, "OP": "+"}
        ]},
        {"label": "DATE", "pattern": [{"SHAPE": "dd.dd.dddd"}]},
        {"label": "DATE", "pattern": [{"SHAPE": "dd.dddd"}]},
        {"label": "DATE", "pattern": [{"SHAPE": "dd", "SPACY": False}, {"TEXT": "-", "SPACY": False}, {"SHAPE": "dd", "SPACY": False}, {"TEXT": "-", "SPACY": False}, {"SHAPE": "dddd"}]},
        {"label": "DATE", "pattern": [{"SHAPE": "dd", "SPACY": False}, {"TEXT": "-", "SPACY": False}, {"SHAPE": "dddd"}]},
        {"label": "DATE", "pattern": [{"SHAPE": "dd", "SPACY": False}, {"TEXT": "/", "SPACY": False}, {"SHAPE": "dd", "SPACY": False}, {"TEXT": "/", "SPACY": False}, {"SHAPE": "dddd"}]},
        {"label": "DATE", "pattern": [{"SHAPE": "dd", "SPACY": False}, {"TEXT": "/", "SPACY": False}, {"SHAPE": "dddd"}]},
        {"label": "DATE", "pattern": [{"SHAPE": "dd."}, {"POS": "NOUN"}, {"SHAPE": "dddd"}]},
    ])

    PER = nlp.vocab["PER"]
    ORG = nlp.vocab["ORG"]

    def rule(doc: Doc):
        doc = entity_ruler(doc)

        for entity in doc.ents:
            entity._.orgx = tuple(components(entity))

        return doc

    return rule

def entities_to_dict(doc: Doc):
    if len(doc.ents) == 0:
        return {}

    PER = doc.vocab["PER"]
    ORG = doc.vocab["ORG"]
    DATE = doc.vocab["DATE"]

    content = {"name": None}
    persons = []

    for ent in doc.ents:
        entity_type = None

        if ent.label == ORG:
            for (orgx, start, end) in ent._.orgx:
                if orgx == OrgX.ORG_TYPE:
                    entity_type = clean_text(ent[start:end])
        elif ent.label == PER:
            person = {"name": None}

            for (orgx, start, end) in ent._.orgx:
                match orgx:
                    case OrgX.PER_POSITION:
                        entity_type = clean_text(ent[start:end])
                        person["positionType"] = entity_type
                    case OrgX.PER_SALUTATION:
                        person["salutation"] = clean_text(ent[start:end])
                    case OrgX.PER_TITLE:
                        person["title"]  = clean_text(ent[start:end])
                    case _:
                        person["name"] = clean_text(ent[start:end])

            persons.append(person)
        elif ent.label == DATE:
            content["date"] = ent.text

        if ent.start == 0:
            content["type"] = entity_type
            content["name"] = clean_text(ent)

    if "type" not in content:
        for (orgx, start, end) in components(doc[:doc.ents[0].start]):
            if orgx == OrgX.ORG_TYPE:
                content["type"] = clean_text(doc[start:end])

    content["persons"] = persons

    return content

def merge_dicts(spacy_extracted, llm_extracted):
    # Clean llm output
    confabulated = set(llm_extracted.get("error", {}).get("confabulated", []))
    name = llm_extracted.get("name")

    if name != None:
        type = llm_extracted.get("type")

        if type != None:
            if type != name:
                name = name.removeprefix(type).lstrip()
        else:
            llm_extracted.pop("type", None)

        name = remove_confabulated_parts(name, confabulated)

        if 0 < len(name):
            llm_extracted["name"] = name
        else:
            llm_extracted.pop("name", None)

    for person in llm_extracted.get("persons", []):
        name = person.get("name")

        if name != None:
            position_type = person.get("positionType")
            salutation = person.get("salutation")
            title = person.get("title")

            if position_type != None and position_type != "N.N." and position_type != "N. N.":
                if position_type != name:
                    name = name.removeprefix(position_type).lstrip()

                position_type = remove_confabulated_parts(position_type, confabulated)

                if 0 < len(position_type):
                    person["positionType"] = position_type
                else:
                    person.pop("positionType", None)
            else:
                person.pop("positionType", None)

            if salutation != None:
                if salutation != name:
                    name = name.removeprefix(salutation).lstrip()

                salutation = remove_confabulated_parts(salutation, confabulated)

                if 0 < len(salutation):
                    person["salutation"] = salutation
                else:
                    person.pop("salutation", None)
            else:
                person.pop("salutation", None)

            if title != None:
                if title != name:
                    name = name.removeprefix(title).lstrip()

                title = remove_confabulated_parts(title, confabulated)

                if 0 < len(title):
                    person["title"] = title
                else:
                    person.pop("title", None)
            else:
                person.pop("title", None)

            name = remove_confabulated_parts(name, confabulated)

            if 0 < len(name):
                person["name"] = name
            else:
                person.pop("name", None)

    for (llm_key, llm_value) in llm_extracted.items():
        if llm_value == None:
            continue

        spacy_value = spacy_extracted.get(llm_key)
    
        if spacy_value == None:
            spacy_extracted[llm_key] = llm_value

        spacy_persons = spacy_extracted.get("persons", [])
        llm_persons = llm_extracted.get("persons", [])
        count = len(spacy_persons)

        for llm_person in llm_persons:
            has_match = False

            for i in range(0, count):
                spacy_person = spacy_persons[i]

                if spacy_person.get("name") == llm_person.get("name"):
                    for (key, value) in llm_person.items():
                        if spacy_person.get(key) == None:
                            spacy_person[key] = value

                    has_match = True

            if not has_match:
                spacy_persons.append(llm_person)

        spacy_extracted["persons"] = spacy_persons + llm_persons[count:]

    return spacy_extracted

def remove_confabulated_parts(name: str, confabulated):
    new_name = ""

    for part in name.split():
        if part not in confabulated:
            new_name += part + " "

    return new_name.rstrip()

def components(entity: Span):
    start = 0

    for end in range(1, len(entity)):
        if entity[end - 1]._.orgx != entity[end]._.orgx:
            yield (entity[end - 1]._.orgx, start, end)
            start = end

    if start < len(entity):
        yield (entity[start]._.orgx, start, len(entity))

def clean_text(span: Span):
    SP = span.doc.vocab["_SP"]
    fn = lambda token: token.text_with_ws if token.tag != SP else " "
    return "".join(map(fn, span)).strip()

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
