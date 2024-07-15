import json
import os
import string
import llm
import ntpath
import sys
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

async def extract_from_content(llm: Model, content: Sequence[ContentNode], schema, max_concurrency=5):
    loop = asyncio.get_running_loop()
    executor = ThreadPoolExecutor(max_workers=max_concurrency)

    total_tasks = len(content)
    completed_tasks = 0
    tasks = []

    async def run_task(node):
        nonlocal completed_tasks
        text_content = '\n'.join(line.text for line in node.block)
        result = await loop.run_in_executor(executor, parse_node_llm, llm, text_content, schema)
        completed_tasks += 1
        print_progress_bar(completed_tasks, total_tasks)
        return result

    for node in content:
        cleanup_node(node)
        merge_textblocks(node.block)
        tasks.append(run_task(node))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results


def parse_node_llm(llm: Model, text_content: str, schema: str):
    response = llm.prompt('''You are a model that parses unstructured content from organizational charts into a provided json schema. Only provide the resulting json without any other text or comments. You should not add any additional data under any circumstance. If you can't find some information, leave the field to null. The "name" field after type usually consists of the previously found "type" and an additional identifier like numbers or letters. The contact field only consists of numbers. Here is an example of a parsed entity: { "type": "Abteilung", "name": "Abteilung V", "persons": [{ "name": "MD Schröder", "positionType": "MD" }] "responsibilities": [ "Föderale Finanzbeziehungen", "Staats- und Verfassungsrecht", "Rechtsangelegenheiten" "Historiker-Kommission" ] } The json schema looks like this:''' + schema + '. And this is the provided content: ' + text_content, temperature=0)

    response_json = {}
    org_type = find_org_type(text_content)
    try:
        response_json = json.loads(response.text(), strict = False)
        if org_type is not None:
            response_json['type'] = org_type
    except Exception as e:
        print('ERROR: Invalid json', e, file=sys.stderr)
        try:
            response_json = json.loads(repair_json(response.text()), strict = False)
        except Exception as e:
            print('ERROR: Could not fix json. Writing raw content', file=sys.stderr)
            response_json['raw'] = text_content

    response_values = collect_values(response_json)

    # remove all puncutation to make it easier to compare the provided content to the content generated by LLM
    provided_content = text_content.lower().translate(str.maketrans('', '', string.punctuation))
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

    print(response_json)
    return response_json

def print_progress_bar(iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
    if iteration == total: 
        print()

async def extract_from_file(file_path: str, output_path: str, model, schema):
        page = pymupdf.open(file_path)[0]
        (_, _, _, _, content_nodes) = extract(page)


        start = timeit.default_timer()
        extract_results = await extract_from_content(model, content_nodes, str(schema), max_concurrency=5)

        head, tail = ntpath.split(file_path)
        file_name = tail or ntpath.basename(head)
        output_json = {
            "fileName": file_name,
            "content" : extract_results
        }
        
        end = timeit.default_timer()
        print("took", end - start)

        if output_path:
            with open(output_path, 'w+', encoding='utf-8') as out:
                json.dump(output_json, out, ensure_ascii=False)
        else:
            print(json.dumps(output_json, ensure_ascii=False, indent=2))

async def parse(input_path: str, output_file: str, model_name: str, schema_path: str):
    model: Model = llm.get_model(model_name)
    model.key = os.environ['API_KEY']
    schema = load_json(schema_path)

    if ntpath.isfile(input_path):
        await extract_from_file(input_path, output_file, model, schema)
    elif ntpath.isdir(input_path):
        print("parse orgcharts from directory")
        for file in os.listdir(input_path):
            head, _ = file.split(".")
            out_name, ending = output_file.split(".")
            out_file = f"{out_name}_{head}.{ending}"
            await extract_from_file(file, out_file, model, schema)
    else:
        print("file path does not exists", file=sys.stderr)
