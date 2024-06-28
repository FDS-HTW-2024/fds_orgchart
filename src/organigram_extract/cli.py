import argparse
from .person_data import parse

def run():
    parser = argparse.ArgumentParser(prog='Organigramm Extract')

    parser.add_argument('filename', help='source file for extraction')
    parser.add_argument('-o', '--output_file', help='output file to write the extracted content')
    parser.add_argument('-m' '--model', help='model to use for content extraction', default= "gpt-3.5-turbo")
    
    args = parser.parse_args()
    parse(args.filename)
