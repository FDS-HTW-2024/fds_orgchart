import json
import os
import string
import itertools
import llm
from organigram_extract.data import TextLine, ContentNode
from organigram_extract.extract import extract
from fix_busted_json import repair_json
from fix_busted_json import first_json 
import pymupdf
from typing import List

def load_json(path: str):
    with open(path, 'r', encoding='utf-8') as file:
        data = json.load(file)
        return data

org_types = load_json("./example_data/org_types.json")
person_prefix = load_json("./example_data/person_prefixes.json")

def find_org_type(text):
    for element in org_types:
        if text.startswith(element):
            return element
    return None 

chars_to_remove = '(){}[]'
trailing_to_remove = '.-'
def find_person(text):
    for prefix in person_prefix:
        if text.startswith(prefix):
            text = ''.join([char for char in text if char not in chars_to_remove and not char.isdigit()])
            text = text.rstrip(trailing_to_remove)
            return text
    return None 

def find_bezeichnung(text):
    return text

connecting_words = ['für', 'und', '/', ',', '-']
def merge_textblocks(list: list[TextLine]):
    '''Merges TextLines that semantically
    belong together based off of connection words'''
    idx = 1
    while idx < len(list):
        not_found = True 
        for con in connecting_words:
            text = list[idx - 1]
            if text.text.endswith(con):
                text.text += " " + list[idx].text
                del list[idx]
                not_found = False 
        idx += int(not_found)

def cleanup_node(node):
    '''Removes duplicate TextLines from ContentNode
    and trims whitespace caracters'''
    unique_text_blocks: List[TextLine] = list()
    seen = set()

    for text_block in node.block:
        if text_block.text not in seen:
            unique_text_blocks.append(text_block)
            seen.add(text_block.text)

def parse_node(node):
    art = None
    bezeichnung = None
    persons = []
    titel = None
    zusatzbezeichnung = None

    cleanup_node(node) 
    merge_textblocks(node.block)
    for text_block in node.block:
        text = text_block.text
        if not art:
            art = find_org_type(text)
            if art: 
                bezeichnung = text
            continue
        if len(persons) == 0:
            person = find_person(text)
            if person:
                persons.append(person)
    return (art, bezeichnung, persons, titel, zusatzbezeichnung)

def collect_values(json, collected=None):
    if collected is None:
        collected = []

    if isinstance(json, dict):
        for _, value in json.items():
            if isinstance(value, (dict, list)):
                collect_values(value, collected)
            else:
                collected.append(value)
    elif isinstance(json, list):
        for item in json:
            if isinstance(item, (dict, list)):
                collect_values(item, collected)
            else:
                collected.append(item)
    else:
        collected.append(json)

    return collected

def parse_node_llm(node: ContentNode, model, schema):
    cleanup_node(node)
    merge_textblocks(node.block)

    text_content = '\n'.join(line.text for line in node.block)
    # print(text_content)
    response = model.prompt('''You are a model that parses unstructured content from Organizational charts into a provided json schema. Only provide the resulting json without any other text or comments. You should not add any additional data under any circumstance. If you can't find some information, leave the field to null. The "name" field after type usually consists of the previously found "type" and an additional identifier like numbers or letters. The contact field only consists of numbers. Here is an example of a parsed entity: { "type": "Abteilung", "name": "Abteilung V",     "persons": [ { "name": "MD Schröder", "positionType": "MD" } ] "responsibilities": [ "Föderale Finanzbeziehungen", "Staats- und Verfassungsrecht", "Rechtsangelegenheiten" "Historiker-Kommission" ] } The json schema looks like this:''' + str(schema) + '. And this is the provided content: ' + str(text_content))

    response_json = {"name": response.text()}
    try:
        response_json = json.loads(response.text(), strict = False)
    except Exception as e:
        print('ERROR: Invalid json', e)
        print('Trying to fix json...')
        print('Response', response.text())
        response_json = json.loads(repair_json(response.text()), strict = False)

    response_values = collect_values(response_json)

    original_content = text_content.lower().translate(str.maketrans('', '', string.punctuation)).split()
    collected_cleared = str(response_values).lower().translate(str.maketrans('', '', string.punctuation)).split()

    not_sorted = []
    hallucinated = []
    for word in original_content:
        if word not in collected_cleared:
            not_sorted.append(word)

    for word in collected_cleared:
        if word not in original_content:
            hallucinated.append(word)

    if 'unsorted' not in response_json or not isinstance(response_json['unsorted'], list):
        response_json['unsorted'] = []

    response_json['unsorted'].extend(not_sorted)
    print('Not sorted', not_sorted)
    print(response_json)

    return response_json 

def print_progress_bar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
    if iteration == total: 
        print()

def parse(input_file: str, output_file: str, model_name: str, schema_path: str):
    page = pymupdf.open(input_file)[3]
    (rectangles, lines, junctions, words, content_nodes) = extract(page)

    model = llm.get_model(model_name)
    model.key = os.environ['API_KEY']
    schema = load_json(schema_path)

    #replace with len(content_nodes) later
    max_content_nodes = min(len(content_nodes), 30)

    json_nodes = []
    for i, node in itertools.islice(enumerate(content_nodes), 0, max_content_nodes):
        llm_parsed = parse_node_llm(node, model, schema)
        json_nodes.append(llm_parsed)

        if not output_file:
            print(llm_parsed)
        print_progress_bar(i + 1, max_content_nodes, 'Progress', 'Complete')
    
    if output_file:
        with open(output_file, 'w+', encoding='utf-8') as out:
            json.dump({"content" : json_nodes}, out, ensure_ascii=False)
    else:
        print(json.dumps({"content": json_nodes}, ensure_ascii=False, indent=2))
