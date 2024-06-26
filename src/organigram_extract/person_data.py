import json
import re
from collections import defaultdict
from organigram_extract.data import Rect, TextLine, ContentNode, Point
from organigram_extract.extract import extract
import pymupdf
from typing import List

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

    for text in node.block:
        text.text = text.text.strip(' \n')
        text.text = text.text.replace('\n', '')
        text.text = re.sub(' +', ' ', text.text)
        print(text.text)

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
    page = pymupdf.open(filename)[0]
    (rectangles, lines, junctions, words, content_nodes) = extract(page)

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
        print('---------------------------------------------')

    print("Unfiltered: ", len(records))
    print("Filtered: ", len(unique_records))
