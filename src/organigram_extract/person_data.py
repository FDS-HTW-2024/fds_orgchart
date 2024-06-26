import json
import re
from collections import defaultdict
from organigram_extract.data import Rectangle, TextBlock, ContentNode, Point
from organigram_extract.extract import extract
from typing import List

def point_from_dict(data: dict) -> Point:
    return Point(x=data['x'], y=data['y'])

def rectangle_from_dict(data: dict) -> Rectangle:
    return Rectangle(
        top_left=point_from_dict(data['top_left']),
        bottom_right=point_from_dict(data['bottom_right'])
    )

def textblock_from_dict(data: dict) -> TextBlock:
    return TextBlock(
        bounding_box=rectangle_from_dict(data['bounding_box']),
        content=data['content']
    )

def contentnode_from_dict(data: dict) -> ContentNode:
    return ContentNode(
        rect=rectangle_from_dict(data['rect']),
        content=[textblock_from_dict(tb) for tb in data['content']]
    )

def load_content_nodes(path: str):
    with open(path, 'r', encoding='utf-8') as file:
        data = json.load(file)
        return [contentnode_from_dict(node) for node in data]

def load_json(path: str):
    with open(path, 'r', encoding='utf-8') as file:
        data = json.load(file)
        return data

art_elements = load_json("./example_data/art_elements.json")
person_prefix = load_json("./example_data/person_prefixes.json")

def find_best_art(text):
    for element in art_elements:
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

def create_text_block(list: list[TextBlock]):
    idx = 1
    while idx < len(list):
        not_found = True 
        for con in connecting_words:
            text = list[idx - 1]
            if text.content.endswith(con):
                text.content += ' ' + list[idx].content
                del list[idx]
                not_found = False 
        idx += int(not_found)

word_count = defaultdict(int)
def cleanup_node(node):
    unique_text_blocks: List[TextBlock] = list()
    for text in node.content:
        if text not in unique_text_blocks:
            unique_text_blocks.append(text)
    
    node.content = unique_text_blocks
    for text in node.content:
        text.content = text.content.strip(' \n')
        text.content = text.content.replace('\n', '')
        text.content = re.sub(' +', ' ', text.content)
        print(text.content)

def parse_node(node):
    art = None
    bezeichnung = None
    persons = []
    titel = None
    zusatzbezeichnung = None

    cleanup_node(node) 
    create_text_block(node.content)
    for text_block in node.content:
        text = text_block.content
        if not art:
            art = find_best_art(text)
            if art: 
                bezeichnung = text
            continue
        if len(persons) == 0:
            person = find_person(text)
            if person:
                persons.append(person)
    return (art, bezeichnung, persons, titel, zusatzbezeichnung)

def parse(filename: str):
    records = []
    (rectangles, lines, junctions, words, content_nodes) = extract(filename)

    for node in content_nodes:
        (art, bezeichnung, persons, titel, zusatzbezeichnung) = parse_node(node)
        records.append((art, bezeichnung, tuple(persons), titel, zusatzbezeichnung))

    unique_records = []
    seen = set()

    for record in records:
        if record not in seen:
            unique_records.append(record)
            seen.add(record)

    for rec in unique_records:
        print(rec)
        print('=====')

    print(len(unique_records))
