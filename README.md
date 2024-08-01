# Extraction of Structure of German Organizational Charts

This repository contains the orgxtract package and CLI.

## Development

We develop with Pipenv. A guide for setting up a dev environment is on the [The Hitchhiker’s Guide to Python](https://docs.python-guide.org/).

## Installation

To run the project Python 3 and a package installer/manager must be installed that can handle pyproject.toml. The following installation steps use Pipenv as example.

Install all dependencies in a virtual environment.
```
pipenv install -e .
```

Install the spacy German model.
```
pipenv run python -m spacy download de_core_news_md
```

## Usage

This is a basic example to extract data from the first page of a PDF.
```py
from orgxtract import Document, TextPipeline
import orgxtract.pdf as pdf

# Return the first page of the PDF
drawing = next(pdf.open("examples/orgchart.pdf"))
document = Document.extract(drawing)

# The with statement is only necessary when using threads.
with TextPipeline() as text_pipeline:
	texts = document.text_contents.values()

	for content in text_pipeline.pipe(texts):
		print(content)
```

## CLI

This package contains a command line tool. It can be executed by running it as script.

The input can be either a PDF or a directory containing multiple PDFs.
```
pipenv run python -m orgxtract path/to/input -o path/to/output
```
Use `--help` to see all parameters

## License

TBD
