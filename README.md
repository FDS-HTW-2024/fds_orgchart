# Extraction of Structure of German Organizational Charts

## Installation

To run the project Python 3, Pip and Pipenv must be installed. A guide for setting up a dev environment is on the [The Hitchhiker’s Guide to Python](https://docs.python-guide.org/).

Install all dependencies in a virtual environment managed by Pipenv.
```
pipenv install -e .
```

Install the spacy German model.
```
pipenv run python -m spacy download de_core_news_md
```

## CLI

This package contains a command line tool. It can be executed by running it as script.

The input can be either a PDF or a directory containing multiple PDFs.
```
pipenv run python -m orgxtract path/to/input -o path/to/output
```
Use `--help` to see all parameters

## Build

TBD

## License

TBD
