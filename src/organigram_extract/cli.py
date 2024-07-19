import argparse
from concurrent.futures import as_completed, ThreadPoolExecutor
import json
from queue import Queue

from organigram_extract import Document, Drawing, TextPipeline
import organigram_extract.pdf as pdf

def run():
    parser = argparse.ArgumentParser(prog='Organigramm Extract')

    parser.add_argument('filename', help='source file for extraction')
    parser.add_argument('-o', '--output_file', help='output file to write the extracted content')
    
    args = parser.parse_args()

    worker_threads = 8

    with ThreadPoolExecutor(max_workers=worker_threads) as executor:
        task_queue = Queue(1)

        # Process all text in a separate thread
        #
        # The text pipeline components are created once to avoid using too
        # much memory accidentally.
        text_processing = executor.submit(process_text, task_queue)

        tasks = [executor.submit(process_drawing, id, drawing, task_queue)
                 for (id, drawing) in enumerate(pdf.open(args.filename))]

        for future in as_completed(tasks):
            results = future.result()
            print("=========")
            print(json.dumps(results))

        # Shutdown text processing thread
        task_queue.put(None)
        text_processing.result()

def process_drawing(id: int, drawing: Drawing, task_queue: Queue):
    document = Document.extract(drawing)
    inputs = tuple(document.text_contents.values())

    if len(inputs) == 0:
        return []

    oneshot = Queue(1)

    task_queue.put((oneshot, inputs))

    outputs = oneshot.get()
    oneshot.task_done()

    results = list()

    for (rect, output) in zip(document.text_blocks.keys(), outputs):
        if  0 < len(output):
            output["bbox"] = document.rects[rect]
            results.append(output)

    return results

def process_text(task_queue: Queue):
    pipeline = TextPipeline()

    for (oneshot, inputs) in iter(task_queue.get, None):
        outputs = tuple(pipeline.process(inputs))

        oneshot.put(outputs)
