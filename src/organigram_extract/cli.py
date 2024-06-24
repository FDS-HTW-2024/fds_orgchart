import argparse
from .person_data import parse


def run():
    parser = argparse.ArgumentParser(prog='Organigramm Extract')

    parser.add_argument('filename', help='source file for extraction')
    parser.add_argument('-o', '--output_file', help='output file to write the extracted content')
    
    args = parser.parse_args()
    parse(args.filename)

