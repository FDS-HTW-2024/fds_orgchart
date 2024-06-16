import spacy
import json
import csv
import re
from spacy import displacy
from data import Rectangle, TextBlock, ContentNode, Point

nlp = spacy.load("de_core_news_lg")

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
        text_blocks=[textblock_from_dict(tb) for tb in data['content']]
    )

def load_content_nodes(path: str):
    with open(path, 'r', encoding='utf-8') as file:
        data = json.load(file)
        return [contentnode_from_dict(node) for node in data]

def load_art_elements(path: str):
    with open(path, 'r', encoding='utf-8') as file:
        data = json.load(file)
        return data

art_elements = load_art_elements("./example_data/art_elements.json")
person_prefix = load_art_elements("./example_data/person_prefixes.json")
content_nodes = load_content_nodes('./example_data/content_nodes.json') 

def find_best_art(text):
    for element in art_elements:
        if text.startswith(element):
            return element
    return None 

def find_person(text):
    # doc = nlp(text)
    # for ent in doc.ents:
    #     if ent.label_ == "PERSON":
    #         return text
    for prefix in person_prefix:
        if text.startswith(prefix):
            return text
    return None 

def find_bezeichnung(text):
    return text

csv_field = ["Art", "Bezeichnung", "Person", "Titel", "Zusatzbezeichnung", "Datum"]

records = []

def parse_node(node):
    art = None
    bezeichnung = None
    # ggf. nach mehreren Personen suchen
    # Personen: Aus mehreren Faktoren ableiten, ob es sich um eine Person handelt:
    # Prefix: (MDG, etc.) und Spacy nutzen (fuer Namen ohne Prefix)
    persons = []
    titel = None
    zusatzbezeichnung = None
    for text_block in node.text_blocks:
        text = text_block.content
        print(text)
        if not art:
            art = find_best_art(text)
            if art: 
                bezeichnung = text 
            continue
        person = find_person(text)
        if person:
            persons.append(person)
        # if not zusatzbezeichnung:
        #     zusatzbezeichnung = find_bezeichnung(text)
        #     continue
    return (art, bezeichnung, persons, titel, zusatzbezeichnung)


for node in content_nodes:
    records.append(parse_node(node))

print(records)

text_blocks = content_nodes

combined_text= " ".join(block.content for node in content_nodes for block in node.text_blocks)
# doc = nlp(combined_text)
# html = displacy.render(doc, style="ent")

# print(html)

# docs = list(nlp.pipe())
# displacy.serve(doc, style="ent")
