import argparse
from concurrent.futures import as_completed, Executor, ThreadPoolExecutor
import json
from queue import Queue
import sys
from typing import Iterator

from organigram_extract import Document, Drawing, TextPipeline
import organigram_extract.pdf as pdf

def run():
    parser = argparse.ArgumentParser(prog='Organigramm Extract')

    parser.add_argument('filename', help='source file for extraction')
    parser.add_argument('-o', '--output_file', help='output file to write the extracted content')
    
    args = parser.parse_args()

    worker_threads = 8

    with ThreadPoolExecutor(max_workers=worker_threads) as executor:
        results = process(executor, pdf.open(args.filename))
        content = {index:result for (index, result) in enumerate(results)}
        json.dump(content, sys.stdout, ensure_ascii=False)

def process(executor: Executor, drawings: Iterator[Drawing]):
    task_queue = Queue(1)

    # Process all text in a separate thread
    #
    # The text pipeline components are created once to avoid using too
    # much memory accidentally.
    text_processing = executor.submit(process_text, task_queue)

    tasks = executor.map(lambda d: process_drawing(d, task_queue), drawings)

    for result in tasks:
        yield result

    # Shutdown text processing thread
    task_queue.put(None)
    text_processing.result()

def process_drawing(drawing: Drawing, task_queue: Queue):
    document = Document.extract(drawing)

    if len(document.text_blocks) == 0:
        return []

    inputs = tuple(document.text_contents.values())
    oneshot = Queue(1)

    task_queue.put((oneshot, inputs))

    outputs = oneshot.get()
    content = [output for output in outputs if output["type"] != None or 0 < len(output["persons"])]

    return {"content": content}

def process_text(task_queue: Queue):
    pipeline = TextPipeline()

    for (oneshot, inputs) in iter(task_queue.get, None):
        outputs = tuple(pipeline.process(inputs))

        oneshot.put(outputs)
