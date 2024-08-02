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

## Logging

The package does use the Python logging module. It is enabled in the CLI and the level can be configured.

## Data Set

We used a subset from the data from these websites.

- https://www.auswaertiges-amt.de/de/service/terminologie/-/215262
- https://de.wikipedia.org/wiki/Besoldungsordnung_B
- https://www.gesetze-im-internet.de/bbesg/anlage_i.html
- https://www.landesrecht-bw.de/bsbw/document/jlr-AmtsbezZusVBWV14Anlage2
- https://www.verwaltungsvorschriften-im-internet.de/bsvwvbund_13022024_D3302001835.htm
- https://www.verwaltungsvorschriften-im-internet.de/bsvwvbund_14092020_D3302001016.htm
- https://de.wikipedia.org/wiki/Bundesministerium_(Deutschland)

## License

The code is licensed under the MIT license. For distribution, the licenses of the dependencies must be consulted.
