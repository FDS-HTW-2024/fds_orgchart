import json
import os
import string
import llm
import asyncio
from concurrent.futures import ThreadPoolExecutor
import timeit
from llm import Model
from typing import List, Sequence
from organigram_extract.data import TextLine, ContentNode
from organigram_extract.extract import extract
from fix_busted_json import repair_json
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

async def extract_from_content(llm: Model, content: Sequence[ContentNode], schema, max_concurrency=5):
    loop = asyncio.get_running_loop()
    executor = ThreadPoolExecutor(max_workers=max_concurrency)

    tasks = []
    for idx, node in enumerate(content):
        cleanup_node(node)
        merge_textblocks(node.block)
        tasks.append(loop.run_in_executor(executor, parse_node_llm, llm, node, schema))
        print_progress_bar(idx, len(content))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results


def parse_node_llm(llm: Model, node: ContentNode, schema: str):
    text_content = '\n'.join(line.text for line in node.block)
    response = llm.prompt('''You are a model that parses unstructured content from organizational charts into a provided json schema. Only provide the resulting json without any other text or comments. You should not add any additional data under any circumstance. If you can't find some information, leave the field to null. The "name" field after type usually consists of the previously found "type" and an additional identifier like numbers or letters. The contact field only consists of numbers. Here is an example of a parsed entity: { "type": "Abteilung", "name": "Abteilung V", "persons": [{ "name": "MD Schröder", "positionType": "MD" }] "responsibilities": [ "Föderale Finanzbeziehungen", "Staats- und Verfassungsrecht", "Rechtsangelegenheiten" "Historiker-Kommission" ] } The json schema looks like this:''' + schema + '. And this is the provided content: ' + text_content, temperature=0)

    response_json = {}
    try:
        response_json = json.loads(response.text(), strict = False)
    except Exception as e:
        print('ERROR: Invalid json', e)
        try:
            response_json = json.loads(repair_json(response.text()), strict = False)
        except Exception as e:
            print('ERROR: Could not fix json. Writing raw content')
            response_json['raw'] = text_content

    print(response.text())
    response_values = collect_values(response_json)
    #TODO check if keys is in the provided schema (generate key path)
    # maybe mit json schema validator

    original_content = text_content.lower().translate(str.maketrans('', '', string.punctuation)).split()
    collected_cleared = str(response_values).lower().translate(str.maketrans('', '', string.punctuation)).split()

    not_sorted = []
    hallucinated = []
    #TODO texte besser vergleichen 
    for word in original_content:
        if word not in collected_cleared:
            not_sorted.append(word)

    for word in collected_cleared:
        if word not in original_content:
            hallucinated.append(word)

    if 'unsorted' not in response_json:
        response_json['unsorted'] = []
    response_json['unsorted'].extend(not_sorted)
    
    if 'hallucinated' not in response_json:
        response_json['hallucinated'] = []
    response_json['hallucinated'].extend(hallucinated)

    return response_json

def print_progress_bar(iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
    if iteration == total: 
        print()

async def parse(input_file: str, output_file: str, model_name: str, schema_path: str):
    page = pymupdf.open(input_file)[0]
    (_, _, _, _, content_nodes) = extract(page)

    model: Model = llm.get_model(model_name)
    model.key = os.environ['API_KEY']
    schema = load_json(schema_path)

    start = timeit.default_timer()
    extract_results = await extract_from_content(model, content_nodes, str(schema), max_concurrency=5)
    #TODO Orgchart metadata extracten
    end = timeit.default_timer()
    print("took", end - start)
    if output_file:
        with open(output_file, 'w+', encoding='utf-8') as out:
            json.dump({"content" : extract_results}, out, ensure_ascii=False)
    else:
        print(json.dumps({"content": extract_from_content}, ensure_ascii=False, indent=2))
