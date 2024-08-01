from dataclasses import dataclass
import json
import string
from typing import Optional

import llm
from llm import Model
from fix_busted_json import repair_json

@dataclass(slots=True)
class SemanticAnalysis:
    model: Model
    schema: str

    def __init__(self, model_name: str, api_key: Optional[str], schema: str):
        model = llm.get_model(model_name)
        model.key = api_key
        self.model = model
        self.schema = schema

    def analyse(self, text: str):
        llm = self.model
        schema = self.schema

        response = llm.prompt('''You are a model that parses unstructured content from organizational charts into a provided json schema. Only provide the resulting json without any other text or comments. You should not add any additional data under any circumstance. If you can't find some information, leave the field to null. The "name" field after type usually consists of the previously found "type" and an additional identifier like numbers or letters. The contact field only consists of numbers. Here is an example of a parsed entity: { "type": "Abteilung", "name": "Abteilung V", "persons": [{ "name": "MD Schröder", "positionType": "MD" }] "responsibilities": [ "Föderale Finanzbeziehungen", "Staats- und Verfassungsrecht", "Rechtsangelegenheiten" "Historiker-Kommission" ] } The json schema looks like this:''' + schema + '. And this is the provided content: ' + text, temperature=0)

        response_text = response.text()
        response_json = {}

        try:
            response_json = json.loads(response_text, strict = False)
        except Exception:
            try:
                response_json = json.loads(repair_json(response_text), strict = False)
            except Exception:
                raise LlmResponseError(response_text)

        response_values = collect_values(response_json)

        # remove all puncutation to make it easier to compare the provided content to the content generated by LLM
        provided_content = text.lower().translate(str.maketrans('', '', string.punctuation))
        response_content = str(response_values).lower().translate(str.maketrans('', '', string.punctuation))

        not_sorted = []
        hallucinated = []

        # collect content that hasn't been sorted by LLM
        for word in provided_content.split():
            if word not in response_content:
                not_sorted.append(word)

        # collect content that has been added by LLM
        for word in response_content.split():
            if word not in provided_content:
                hallucinated.append(word)

        response_json['unsorted'] = not_sorted
        response_json['hallucinated'] = hallucinated

        return response_json

class LlmResponseError(Exception):
    response: str

    def __init__(self, response: str):
        super().__init__(f"could not parse {repr(response)}")
        self.response = response

def collect_values(json, collected=None):
    if collected is None:
        collected = []

    if isinstance(json, dict):
        for _, value in json.items():
            if isinstance(value, (dict, list)):
                collect_values(value, collected)
            elif value is not None:
                collected.append(value)
    elif isinstance(json, list):
        for item in json:
            if isinstance(item, (dict, list)):
                collect_values(item, collected)
            elif item is not None:
                collected.append(item)
    else:
        collected.append(json)

    return collected
