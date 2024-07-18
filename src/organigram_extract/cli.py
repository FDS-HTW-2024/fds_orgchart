import argparse
from concurrent.futures import as_completed, ThreadPoolExecutor
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
        text_tasks = Queue(1)
        text_results = Queue(1)

        # Process all text in a separate thread
        #
        # The text pipeline components are created once to avoid using too
        # much memory accidentally.
        text_processing = executor.submit(process_text, text_tasks, text_results)

        tasks = [executor.submit(process_drawing, id, drawing, text_tasks, text_results)
                 for (id, drawing) in enumerate(pdf.open(args.filename))]

        for future in as_completed(tasks):
            (document, results) = future.result()
            for text in results:
                print("============")
                print(text)

        # Shutdown text processing thread
        text_tasks.put(None)
        text_processing.result()

def process_drawing(
        id: int,
        drawing: Drawing,
        text_tasks: Queue,
        text_results: Queue):
    print("PROCESS DRAWING...")
    document = Document.extract(drawing)
    inputs = tuple(document.text_contents.values())

    text_tasks.put((id, inputs))

    while True:
        (result_id, outputs) = text_results.get()

        if result_id == id:
            text_results.task_done()
            return (document, outputs)

def process_text(text_tasks: Queue, text_results: Queue):
    print("PROCESS TEXT...")
    pipeline = TextPipeline()

    for (id, inputs) in iter(text_tasks.get, None):
        outputs = tuple(pipeline.process(inputs))

        text_results.put((id, outputs))
