import spacy
import json
import csv
from spacy import displacy
from organigram_extract.data import Rectangle, TextBlock, ContentNode, Point
from organigram_extract.extract import extract

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

def find_person(text):
    for prefix in person_prefix:
        if text.startswith(prefix):
            return text
    return None 

def find_bezeichnung(text):
    return text

def parse_node(node):
    art = None
    bezeichnung = None
    persons = []
    titel = None
    zusatzbezeichnung = None
    for idx, text_block in enumerate(node.content):
        text = text_block.content
        if not art:
            art = find_best_art(text)
            if art: 
                bezeichnung = text
            continue
        person = find_person(text)
        if person:
            persons.append(person)
    return (art, bezeichnung, persons, titel, zusatzbezeichnung)

def parse():
    # csv_field = ["Art", "Bezeichnung", "Person", "Titel", "Zusatzbezeichnung", "Datum"]
    records = []
    (rectangles, lines, junctions, words, content_nodes) = extract("./example_orgcharts/org_bmf_2018.pdf")

    for node in content_nodes:
        (art, bezeichnung, persons, titel, zusatzbezeichnung) = parse_node(node)
        records.append([art, bezeichnung, persons, titel, zusatzbezeichnung])

    unique_records = []
    seen = set()

    for record in records:
        record_tuple = (record[0], record[1], tuple(record[2]), record[3], record[4])  # Convert the list to a tuple so it can be added to a set
        if record_tuple not in seen:
            unique_records.append(record)
            seen.add(record_tuple)

    for rec in unique_records:
        print(rec)
        print('=====')

    print(len(unique_records))
