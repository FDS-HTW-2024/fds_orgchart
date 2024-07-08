import json
from extract import extract
import pymupdf

def json_parser(filename: str, tolerance: float = 1.0):

    page = pymupdf.open("./example_orgcharts/org_inneres.pdf")
    rects, lines, junction_by_line, text, content_nodes = extract(page, tolerance)
    content_nodes = {"contentNodes": content_nodes}
    rects_data = {"rectangles": rects}
    lines_data = {"lines": lines}
    
    # Convert the dictionaries to JSON strings
    rects_json = json.dumps(rects_data, indent=4)
    lines_json = json.dumps(lines_data, indent=4)
    
    # Write the JSON strings to files
    with open('rects.json', 'w') as rects_file:
        rects_file.write(rects_json)
    
    with open('lines.json', 'w') as lines_file:
        lines_file.write(lines_json)