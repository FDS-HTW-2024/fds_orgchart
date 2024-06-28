import argparse
import os
from .person_data import parse

def run():
    parser = argparse.ArgumentParser(prog='Organigramm Extract')

    parser.add_argument('input_path', help='source file for extraction')
    parser.add_argument('-o', '--output_file', help='output file to write the extracted content',
                        default='out.json')
    parser.add_argument('-m', '--model', help='llm to use for content extraction', default= "gpt-3.5-turbo")
    parser.add_argument('-k', '--key', help='specify API Key (overwrites previously specified key)')
    parser.add_argument('-s', '--schema_file', help='path to json schema to use for parsing. Overrides default json schema',
                       default='src/organigram_extract/default_schema.json')

    args = parser.parse_args()

    if args.key:
        os.environ['API_KEY'] = args.key 

    if not os.environ['API_KEY']:
        key = input('Enter API Key (will be stored as env variable): ')
        os.environ['API_KEY'] = key

    #input_path can point to single pdf or folder with pdfs inside
    parse(args.input_path, args.output_file, args.model, args.schema_file)
