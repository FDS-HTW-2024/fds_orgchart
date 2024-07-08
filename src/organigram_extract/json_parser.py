import json
from organigram_extract.extract import extract
import pymupdf

def json_parser(filename: str, tolerance: float = 1.0):

    output_path = "../../json_holder"

    page = pymupdf.open(filename)[0]
    page.remove_rotation()

     # Extract data from the PDF using the extract function
    rects, lines, junction_by_line, text, content_nodes = extract(page, tolerance)

    # Organize the extracted data into dictionaries
    #content_nodes_data = {"contentNodes": content_nodes}
    rects_data = {"rectangles": rects}
    lines_data = {"lines": lines}
    
    # Convert the dictionaries to JSON strings with indentation for readability
    rects_json = json.dumps(rects_data, indent=4)
    lines_json = json.dumps(lines_data, indent=4)
    #content_nodes_json = json.dumps(content_nodes_data, indent=4)
    
    # Write the JSON strings to files
    with open(f'{output_path}/rects.json', 'w') as rects_file:
        rects_file.write(rects_json)
    
    with open(f'{output_path}/lines.json', 'w') as lines_file:
        lines_file.write(lines_json)

    # with open(f'{output_path}/content_nodes.json', 'w') as content_nodes_file:
    #     content_nodes_file.write(content_nodes_json)

# Example usage
json_parser("../../example_orgcharts/org_inneres.pdf")