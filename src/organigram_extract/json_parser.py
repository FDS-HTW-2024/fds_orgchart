import json
from dataclasses import asdict, is_dataclass
from organigram_extract.data import Rect, TextLine, ContentNode
from organigram_extract.extract import extract
import pymupdf

def dataclass_to_dict(obj):
    if is_dataclass(obj):
        result = asdict(obj)
        for key, value in result.items():
            if isinstance(value, list):
                result[key] = [dataclass_to_dict(item) for item in value]
            elif is_dataclass(value):
                result[key] = dataclass_to_dict(value)
        return result
    else:
        return obj

def json_parser(filename: str, tolerance: float = 1.0):

    output_path = "../../json_holder"

    page = pymupdf.open(filename)[0]
    page.remove_rotation()

     # Extract data from the PDF using the extract function
    rects, lines, junction_by_line, text, content_nodes = extract(page, tolerance)
    
    content_nodes_blocks = []
    for node in content_nodes:
        for block_index, data_block in enumerate(node.block):
            data_block = node.block[block_index]
            content_nodes_blocks.append(data_block)

    content_nodes_blocks_dicts = [dataclass_to_dict(block) for block in content_nodes_blocks]

    # Organize the extracted data into dictionaries
    content_nodes_data = {"content_nodes_data": content_nodes_blocks_dicts}
    rects_data = {"rectangles": rects}
    lines_data = {"lines": lines}
    
    # Convert the dictionaries to JSON strings with indentation for readability
    rects_json = json.dumps(rects_data, indent=4)
    lines_json = json.dumps(lines_data, indent=4)
    content_nodes_json = json.dumps(content_nodes_data, ensure_ascii=False, indent=4)
    
    # Write the JSON strings to files
    with open(f'{output_path}/rects.json', 'w') as rects_file:
        rects_file.write(rects_json)
    
    with open(f'{output_path}/lines.json', 'w') as lines_file:
        lines_file.write(lines_json)

    with open(f'{output_path}/content_nodes.json', 'w', encoding='utf-8') as content_nodes_file:
        content_nodes_file.write(content_nodes_json)

# Example usage
json_parser("../../example_orgcharts/org_inneres.pdf")