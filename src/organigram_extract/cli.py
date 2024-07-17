import argparse
import organigram_extract.pdf as pdf
from organigram_extract.extract import extract_document

def run():
    parser = argparse.ArgumentParser(prog='Organigramm Extract')

    parser.add_argument('filename', help='source file for extraction')
    parser.add_argument('-o', '--output_file', help='output file to write the extracted content')
    
    args = parser.parse_args()

    drawings = pdf.open(args.filename)

    for drawing in drawings:
        document = extract_document(drawing)

        for content in document.text_contents.values():
            print("======")
            print(content)
